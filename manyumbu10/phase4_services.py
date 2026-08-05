from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import (
    BlockedUser, CloseFriend, Follow, Hashtag, HiddenReel, MutedUser, Notification, Post,
    Reel, ReelAudienceUser, ReelHashtag, ReelLike, ReelMention, ReelNotInterested, ReelTag,
    SavedReel, Story, StoryAudienceUser, StoryHashtag, StoryHiddenUser, StoryMention,
    StoryPoll, StoryPollOption, StoryPollVote, StoryReaction, StoryView,
)
from .post_services import ALLOWED_IMAGES, ALLOWED_VIDEOS, MAX_VIDEO_SIZE, clean_text, create_notification, extract_hashtags, extract_mentions, normalize_hashtag, validate_user_targets
from .services import can_view_profile, users_blocked_between

MAX_STORY_IMAGE_SIZE = 8 * 1024 * 1024
MAX_STORY_VIDEO_SIZE = 60 * 1024 * 1024
MAX_REEL_SIZE = 120 * 1024 * 1024
REEL_VIEW_THRESHOLD_SECONDS = 3


def story_is_live(story):
    return story.status == Story.STATUS_PUBLISHED and story.expires_at and story.expires_at > timezone.now()


def sync_story_terms(story, author, hashtags=None, mentions=None, selected=None, hidden=None):
    StoryHashtag.objects.filter(story=story).delete()
    for tag in hashtags or extract_hashtags(story.caption):
        name = normalize_hashtag(tag)
        if name:
            hashtag, _ = Hashtag.objects.get_or_create(name=name, defaults={"display_name": name})
            StoryHashtag.objects.get_or_create(story=story, hashtag=hashtag)
    StoryMention.objects.filter(story=story).delete()
    for user in validate_user_targets(author, list(mentions or []) + extract_mentions(story.caption)):
        StoryMention.objects.get_or_create(story=story, user=user)
        create_notification(user, author, "story_mention", message="You were mentioned in a story.")
    StoryAudienceUser.objects.filter(story=story).delete()
    for user in validate_user_targets(author, selected or []):
        StoryAudienceUser.objects.get_or_create(story=story, user=user)
    StoryHiddenUser.objects.filter(story=story).delete()
    for user in validate_user_targets(author, hidden or []):
        StoryHiddenUser.objects.get_or_create(story=story, user=user)


def can_access_story(user, story, include_highlight=False):
    if story.status in {Story.STATUS_DELETED, Story.STATUS_REMOVED}:
        return False
    if not include_highlight and not story_is_live(story) and story.author != user:
        return False
    if users_blocked_between(user, story.author):
        return False
    if story.author != user and not can_view_profile(user, story.author):
        return False
    if StoryHiddenUser.objects.filter(story=story, user=user).exists():
        return False
    if story.author == user:
        return True
    if story.audience == Story.AUDIENCE_EVERYONE:
        return True
    if story.audience == Story.AUDIENCE_FOLLOWERS:
        return Follow.objects.filter(follower=user, following=story.author).exists()
    if story.audience == Story.AUDIENCE_CLOSE_FRIENDS:
        return CloseFriend.objects.filter(owner=story.author, friend=user).exists()
    if story.audience == Story.AUDIENCE_SELECTED:
        return StoryAudienceUser.objects.filter(story=story, user=user).exists()
    if story.audience == Story.AUDIENCE_HIDE_SELECTED:
        return True
    return False


def visible_stories_for(user):
    blocked_pairs = BlockedUser.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list("blocker_id", "blocked_id")
    blocked = {item for pair in blocked_pairs for item in pair if item != user.phone_number}
    muted = MutedUser.objects.filter(owner=user, mute_stories=True).values_list("muted_id", flat=True)
    qs = Story.objects.filter(status=Story.STATUS_PUBLISHED, expires_at__gt=timezone.now()).exclude(author_id__in=blocked).exclude(author_id__in=muted)
    following = Follow.objects.filter(follower=user).values_list("following_id", flat=True)
    close = CloseFriend.objects.filter(friend=user).values_list("owner_id", flat=True)
    selected = StoryAudienceUser.objects.filter(user=user).values_list("story_id", flat=True)
    hidden = StoryHiddenUser.objects.filter(user=user).values_list("story_id", flat=True)
    allowed = Q(author=user) | Q(audience=Story.AUDIENCE_EVERYONE) | Q(audience=Story.AUDIENCE_HIDE_SELECTED) | Q(audience=Story.AUDIENCE_FOLLOWERS, author_id__in=following) | Q(audience=Story.AUDIENCE_CLOSE_FRIENDS, author_id__in=close) | Q(audience=Story.AUDIENCE_SELECTED, id__in=selected)
    private_authors = get_user_model().objects.filter(profile__is_private=True).exclude(phone_number=user.phone_number).exclude(phone_number__in=following).values_list("phone_number", flat=True)
    return qs.filter(allowed).exclude(id__in=hidden).exclude(author_id__in=private_authors).select_related("author", "author__profile").prefetch_related("mentions__user", "hashtags__hashtag", "views", "reactions").order_by("author_id", "published_at")


def validate_story_media(upload):
    if not upload:
        return Story.TYPE_TEXT
    ctype = upload.content_type
    if ctype in ALLOWED_IMAGES:
        if upload.size > MAX_STORY_IMAGE_SIZE:
            raise ValueError("Story image must be 8MB or smaller.")
        return Story.TYPE_IMAGE
    if ctype in ALLOWED_VIDEOS:
        if upload.size > MAX_STORY_VIDEO_SIZE:
            raise ValueError("Story video must be 60MB or smaller.")
        return Story.TYPE_VIDEO
    raise ValueError("Unsupported story media type.")


@transaction.atomic
def create_story(author, payload, upload=None):
    caption = clean_text(payload.get("caption", payload.get("text_overlay", "")), 1000)
    story_type = validate_story_media(upload)
    if story_type == Story.TYPE_TEXT and not caption:
        raise ValueError("Text stories require text when no media is provided.")
    status = payload.get("status", Story.STATUS_PUBLISHED)
    published_at = timezone.now() if status == Story.STATUS_PUBLISHED else None
    story = Story.objects.create(author=author, story_type=story_type, caption=caption, audience=payload.get("audience", Story.AUDIENCE_EVERYONE), background_style=payload.get("background_style", ""), link_url=payload.get("link_url", ""), location_name=payload.get("location_name", ""), sticker_metadata=payload.get("sticker_metadata", {}) if isinstance(payload.get("sticker_metadata", {}), dict) else {}, replies_enabled=str(payload.get("replies_enabled", "true")).lower() != "false", status=status, published_at=published_at, expires_at=(published_at + timedelta(hours=24)) if published_at else None)
    if upload:
        from .models import StoryMedia
        StoryMedia.objects.create(story=story, file=upload, media_type=story_type, file_size=upload.size)
    sync_story_terms(story, author, payload.get("hashtags"), payload.get("mentions"), payload.get("selected_users"), payload.get("hidden_users"))
    poll = payload.get("poll")
    if isinstance(poll, dict):
        options = [str(item).strip() for item in poll.get("options", []) if str(item).strip()]
        if len(options) < 2 or len(options) > 4:
            raise ValueError("Polls require two to four options.")
        story_poll = StoryPoll.objects.create(story=story, question=clean_text(poll.get("question", ""), 180), show_results=bool(poll.get("show_results", True)))
        for index, option in enumerate(options):
            StoryPollOption.objects.create(poll=story_poll, text=clean_text(option, 80), display_order=index)
    return story


def expire_stories():
    return Story.objects.filter(status=Story.STATUS_PUBLISHED, expires_at__lte=timezone.now()).update(status=Story.STATUS_EXPIRED)


def sync_reel_terms(reel, author, hashtags=None, mentions=None, tagged=None, selected=None):
    ReelHashtag.objects.filter(reel=reel).delete()
    for tag in hashtags or extract_hashtags(reel.caption):
        name = normalize_hashtag(tag)
        if name:
            hashtag, _ = Hashtag.objects.get_or_create(name=name, defaults={"display_name": name})
            ReelHashtag.objects.get_or_create(reel=reel, hashtag=hashtag)
    ReelMention.objects.filter(reel=reel).delete()
    for user in validate_user_targets(author, list(mentions or []) + extract_mentions(reel.caption)):
        ReelMention.objects.get_or_create(reel=reel, user=user)
        create_notification(user, author, "reel_mention", message="You were mentioned in a reel.")
    ReelTag.objects.filter(reel=reel).delete()
    for user in validate_user_targets(author, tagged or []):
        ReelTag.objects.get_or_create(reel=reel, user=user)
        create_notification(user, author, "reel_tag", message="You were tagged in a reel.")
    ReelAudienceUser.objects.filter(reel=reel).delete()
    for user in validate_user_targets(author, selected or []):
        ReelAudienceUser.objects.get_or_create(reel=reel, user=user)


def can_access_reel(user, reel):
    if reel.status in {Reel.STATUS_DELETED, Reel.STATUS_REMOVED, Reel.STATUS_FAILED}:
        return False
    if reel.status in {Reel.STATUS_DRAFT, Reel.STATUS_PROCESSING, Reel.STATUS_ARCHIVED} and reel.author != user:
        return False
    if users_blocked_between(user, reel.author):
        return False
    if reel.author != user and not can_view_profile(user, reel.author):
        return False
    if reel.author == user or reel.audience == Post.AUDIENCE_PUBLIC:
        return True
    if reel.audience == Post.AUDIENCE_FOLLOWERS:
        return Follow.objects.filter(follower=user, following=reel.author).exists()
    if reel.audience == Post.AUDIENCE_CLOSE_FRIENDS:
        return CloseFriend.objects.filter(owner=reel.author, friend=user).exists()
    if reel.audience == Post.AUDIENCE_SELECTED:
        return ReelAudienceUser.objects.filter(reel=reel, user=user).exists()
    return False


def visible_reels_for(user):
    blocked_pairs = BlockedUser.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list("blocker_id", "blocked_id")
    blocked = {item for pair in blocked_pairs for item in pair if item != user.phone_number}
    muted = MutedUser.objects.filter(owner=user, mute_posts=True).values_list("muted_id", flat=True)
    hidden = HiddenReel.objects.filter(user=user).values_list("reel_id", flat=True)
    uninterested = ReelNotInterested.objects.filter(user=user).values_list("reel_id", flat=True)
    qs = Reel.objects.filter(status=Reel.STATUS_PUBLISHED, processing_status=Reel.PROCESSING_READY).exclude(author_id__in=blocked).exclude(author_id__in=muted).exclude(id__in=hidden).exclude(id__in=uninterested)
    following = Follow.objects.filter(follower=user).values_list("following_id", flat=True)
    close = CloseFriend.objects.filter(friend=user).values_list("owner_id", flat=True)
    selected = ReelAudienceUser.objects.filter(user=user).values_list("reel_id", flat=True)
    allowed = Q(author=user) | Q(audience=Post.AUDIENCE_PUBLIC) | Q(audience=Post.AUDIENCE_FOLLOWERS, author_id__in=following) | Q(audience=Post.AUDIENCE_CLOSE_FRIENDS, author_id__in=close) | Q(audience=Post.AUDIENCE_SELECTED, id__in=selected)
    private_authors = get_user_model().objects.filter(profile__is_private=True).exclude(phone_number=user.phone_number).exclude(phone_number__in=following).values_list("phone_number", flat=True)
    return qs.filter(allowed).exclude(author_id__in=private_authors).select_related("author", "author__profile").prefetch_related("hashtags__hashtag", "mentions__user", "tagged_users__user").annotate(like_total=Count("likes", distinct=True), comment_total=Count("comments", filter=Q(comments__is_deleted=False), distinct=True)).order_by("-published_at", "-created_at")


def validate_reel_video(upload):
    if not upload:
        raise ValueError("Reel video is required.")
    if upload.content_type not in ALLOWED_VIDEOS:
        raise ValueError("Unsupported reel video type.")
    if upload.size > MAX_REEL_SIZE:
        raise ValueError("Reel video must be 120MB or smaller.")


@transaction.atomic
def create_reel(author, payload, upload=None, cover=None):
    validate_reel_video(upload)
    status = payload.get("status", Reel.STATUS_PUBLISHED)
    processing = Reel.PROCESSING_READY if status == Reel.STATUS_PUBLISHED else Reel.PROCESSING_PENDING
    published_at = timezone.now() if status == Reel.STATUS_PUBLISHED else None
    reel = Reel.objects.create(author=author, caption=clean_text(payload.get("caption", ""), 2200), audience=payload.get("audience", Post.AUDIENCE_PUBLIC), comments_enabled=str(payload.get("comments_enabled", "true")).lower() != "false", status=status, location_name=clean_text(payload.get("location_name", ""), 140), video=upload, cover_image=cover, duration=float(payload.get("duration", 0) or 0), width=int(payload.get("width", 0) or 0) or None, height=int(payload.get("height", 0) or 0) or None, aspect_ratio=payload.get("aspect_ratio", ""), processing_status=processing, published_at=published_at)
    sync_reel_terms(reel, author, payload.get("hashtags"), payload.get("mentions"), payload.get("tagged_users"), payload.get("selected_users"))
    return reel
