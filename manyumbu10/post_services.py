import re
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import (
    BlockedUser,
    CloseFriend,
    Follow,
    Hashtag,
    HiddenPost,
    MutedUser,
    Notification,
    Post,
    PostAudienceUser,
    PostHashtag,
    PostLike,
    PostMedia,
    PostMention,
    PostTag,
    SavedPost,
)
from .services import can_view_profile, ensure_profile_records, users_blocked_between

HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_]{1,80})")
MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_]{3,50})")
MAX_IMAGES = 10
MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_VIDEO_SIZE = 80 * 1024 * 1024
ALLOWED_IMAGES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEOS = {"video/mp4", "video/quicktime", "video/webm"}


def clean_text(value: str, limit: int) -> str:
    text = (value or "").strip().replace("<", "&lt;").replace(">", "&gt;")
    if len(text) > limit:
        raise ValueError(f"Text must be {limit} characters or fewer.")
    return text


def normalize_hashtag(value: str) -> str:
    return value.strip().lstrip("#").lower()


def extract_hashtags(caption: str):
    seen = []
    for match in HASHTAG_RE.findall(caption or ""):
        tag = normalize_hashtag(match)
        if tag and tag not in seen:
            seen.append(tag)
    return seen


def extract_mentions(caption: str):
    seen = []
    for match in MENTION_RE.findall(caption or ""):
        username = match.lower()
        if username not in seen:
            seen.append(username)
    return seen


def blocked_ids_for(user):
    pairs = BlockedUser.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list("blocker_id", "blocked_id")
    return {item for pair in pairs for item in pair if item != user.phone_number}


def validate_user_targets(actor, usernames):
    User = get_user_model()
    targets = []
    for username in usernames or []:
        target = User.objects.filter(username__iexact=str(username).strip()).first()
        if not target:
            raise ValueError(f"User {username} was not found.")
        if target == actor or users_blocked_between(actor, target):
            raise PermissionError("Blocked users cannot be tagged, mentioned, or selected.")
        targets.append(target)
    return targets


def media_kind(upload):
    ctype = getattr(upload, "content_type", "")
    if ctype in ALLOWED_IMAGES:
        return PostMedia.MEDIA_IMAGE
    if ctype in ALLOWED_VIDEOS:
        return PostMedia.MEDIA_VIDEO
    raise ValueError("Unsupported media type.")


def validate_media(files):
    files = list(files or [])
    if not files:
        return Post.TYPE_TEXT
    kinds = [media_kind(f) for f in files]
    if PostMedia.MEDIA_VIDEO in kinds:
        if len(files) > 1 or any(kind != PostMedia.MEDIA_VIDEO for kind in kinds):
            raise ValueError("A post may contain one video or up to 10 images, not mixed media.")
        if files[0].size > MAX_VIDEO_SIZE:
            raise ValueError("Video must be 80MB or smaller.")
        return Post.TYPE_VIDEO
    if len(files) > MAX_IMAGES:
        raise ValueError("A post can include at most 10 images.")
    for file in files:
        if file.size > MAX_IMAGE_SIZE:
            raise ValueError("Each image must be 8MB or smaller.")
    return Post.TYPE_IMAGE


def create_notification(recipient, actor, notification_type, post=None, comment=None, message=""):
    if recipient == actor:
        return None
    return Notification.objects.get_or_create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        post=post,
        comment=comment,
        defaults={"message": message[:180]},
    )[0]


def sync_post_terms(post, author, hashtags=None, mentions=None, tagged=None, selected=None):
    PostHashtag.objects.filter(post=post).delete()
    for tag_name in hashtags or extract_hashtags(post.caption):
        normalized = normalize_hashtag(tag_name)
        if normalized:
            hashtag, _ = Hashtag.objects.get_or_create(name=normalized, defaults={"display_name": normalized})
            PostHashtag.objects.get_or_create(post=post, hashtag=hashtag)

    PostMention.objects.filter(post=post).delete()
    for user in validate_user_targets(author, list(mentions or []) + extract_mentions(post.caption)):
        PostMention.objects.get_or_create(post=post, user=user)
        create_notification(user, author, Notification.TYPE_POST_MENTION, post=post, message="You were mentioned in a post.")

    PostTag.objects.filter(post=post).delete()
    for user in validate_user_targets(author, tagged or []):
        PostTag.objects.get_or_create(post=post, user=user)
        create_notification(user, author, Notification.TYPE_POST_TAG, post=post, message="You were tagged in a post.")

    PostAudienceUser.objects.filter(post=post).delete()
    for user in validate_user_targets(author, selected or []):
        PostAudienceUser.objects.get_or_create(post=post, user=user)


def can_access_post(user, post):
    if post.status == Post.STATUS_DELETED or post.status == Post.STATUS_REMOVED:
        return False
    if post.status == Post.STATUS_ARCHIVED and post.author != user:
        return False
    if post.status == Post.STATUS_DRAFT and post.author != user:
        return False
    if users_blocked_between(user, post.author):
        return False
    if post.author != user and not can_view_profile(user, post.author):
        return False
    if post.audience == Post.AUDIENCE_PUBLIC:
        return True
    if post.author == user:
        return True
    if post.audience == Post.AUDIENCE_FOLLOWERS:
        return Follow.objects.filter(follower=user, following=post.author).exists()
    if post.audience == Post.AUDIENCE_CLOSE_FRIENDS:
        return CloseFriend.objects.filter(owner=post.author, friend=user).exists()
    if post.audience == Post.AUDIENCE_SELECTED:
        return PostAudienceUser.objects.filter(post=post, user=user).exists()
    if post.audience == Post.AUDIENCE_ONLY_ME:
        return False
    return False


def visible_posts_for(user):
    blocked = blocked_ids_for(user)
    muted = MutedUser.objects.filter(owner=user, mute_posts=True).values_list("muted_id", flat=True)
    hidden = HiddenPost.objects.filter(user=user).values_list("post_id", flat=True)
    base = Post.objects.filter(status=Post.STATUS_PUBLISHED).exclude(author_id__in=blocked).exclude(author_id__in=muted).exclude(id__in=hidden)
    following = Follow.objects.filter(follower=user).values_list("following_id", flat=True)
    close_friends = CloseFriend.objects.filter(friend=user).values_list("owner_id", flat=True)
    selected = PostAudienceUser.objects.filter(user=user).values_list("post_id", flat=True)
    allowed = Q(author=user) | Q(audience=Post.AUDIENCE_PUBLIC) | Q(audience=Post.AUDIENCE_FOLLOWERS, author_id__in=following) | Q(audience=Post.AUDIENCE_CLOSE_FRIENDS, author_id__in=close_friends) | Q(audience=Post.AUDIENCE_SELECTED, id__in=selected)
    private_authors = get_user_model().objects.filter(profile__is_private=True).exclude(phone_number=user.phone_number).exclude(phone_number__in=following).values_list("phone_number", flat=True)
    return base.filter(allowed).exclude(author_id__in=private_authors).select_related("author", "author__profile").prefetch_related("media", "hashtags__hashtag", "tagged_users__user", "mentions__user").annotate(like_total=Count("likes", distinct=True), comment_total=Count("comments", filter=Q(comments__is_deleted=False), distinct=True)).order_by("-published_at", "-created_at")


@transaction.atomic
def create_post(author, payload, files):
    caption = clean_text(payload.get("caption", ""), 2200)
    files = list(files or [])
    if not caption and not files:
        raise ValueError("Post must include text or media.")
    post_type = validate_media(files)
    status = payload.get("status", Post.STATUS_PUBLISHED)
    if status not in {Post.STATUS_DRAFT, Post.STATUS_PUBLISHED}:
        raise ValueError("Posts can only be saved as draft or published from the composer.")
    audience = payload.get("audience", Post.AUDIENCE_PUBLIC)
    post = Post.objects.create(
        author=author,
        caption=caption,
        post_type=post_type,
        audience=audience,
        comments_enabled=str(payload.get("comments_enabled", "true")).lower() != "false",
        status=status,
        location_name=clean_text(payload.get("location_name", ""), 140),
        published_at=timezone.now() if status == Post.STATUS_PUBLISHED else None,
    )
    for index, file in enumerate(files):
        PostMedia.objects.create(post=post, file=file, media_type=media_kind(file), file_size=file.size, display_order=index)
    sync_post_terms(post, author, payload.get("hashtags"), payload.get("mentions"), payload.get("tagged_users"), payload.get("selected_users"))
    return post


@transaction.atomic
def edit_post(post, author, payload):
    if post.author != author:
        raise PermissionError("Only the post owner can edit this post.")
    for field, limit in [("caption", 2200), ("location_name", 140)]:
        if field in payload:
            setattr(post, field, clean_text(payload[field], limit))
    for field in ["audience", "comments_enabled"]:
        if field in payload:
            setattr(post, field, payload[field])
    post.is_edited = True
    if post.status == Post.STATUS_DRAFT and payload.get("status") == Post.STATUS_PUBLISHED:
        post.status = Post.STATUS_PUBLISHED
        post.published_at = timezone.now()
    post.save()
    sync_post_terms(post, author, payload.get("hashtags"), payload.get("mentions"), payload.get("tagged_users"), payload.get("selected_users"))
    return post
