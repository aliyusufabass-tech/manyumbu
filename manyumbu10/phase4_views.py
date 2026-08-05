import json
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import (
    AdminAuditLog, CommentLike, HiddenReel, MutedUser, Notification, Post, PostReport, Reel, ReelComment,
    ReelLike, ReelNotInterested, ReelReport, ReelView, SavedReel, Story, StoryHighlight, StoryHighlightItem,
    StoryPollOption, StoryPollVote, StoryReaction, StoryReply, StoryReport, StoryView,
)
from .phase4_services import can_access_reel, can_access_story, create_reel, create_story, expire_stories, visible_reels_for, visible_stories_for, REEL_VIEW_THRESHOLD_SECONDS
from .post_services import clean_text, create_notification
from .profile_views import AuthenticatedView, compact_user, page
from .views import body, response


def parse_payload(request):
    if request.content_type and request.content_type.startswith("multipart/"):
        payload = request.POST.dict()
        for key in ["hashtags", "mentions", "tagged_users", "selected_users", "hidden_users", "poll"]:
            if key in payload:
                try:
                    payload[key] = json.loads(payload[key])
                except Exception:
                    payload[key] = [item.strip() for item in str(payload[key]).split(",") if item.strip()]
        return payload
    return body(request)


def story_payload(story, viewer):
    media = getattr(story, "media", None)
    poll = getattr(story, "poll", None)
    poll_data = None
    if poll:
        total = poll.votes.count()
        poll_data = {"id": poll.id, "question": poll.question, "total_votes": total, "options": [{"id": opt.id, "text": opt.text, "votes": opt.votes.count(), "percentage": round((opt.votes.count() / total) * 100, 1) if total else 0} for opt in poll.options.order_by("display_order")]}
    return {"id": str(story.id), "author": compact_user(story.author, viewer), "story_type": story.story_type, "caption": story.caption, "audience": story.audience if story.author == viewer else None, "background_style": story.background_style, "link_url": story.link_url, "location_name": story.location_name, "sticker_metadata": story.sticker_metadata, "replies_enabled": story.replies_enabled, "status": story.status, "published_at": story.published_at.isoformat() if story.published_at else None, "expires_at": story.expires_at.isoformat() if story.expires_at else None, "media": {"url": media.file.url, "media_type": media.media_type, "file_size": media.file_size} if media and media.file else None, "hashtags": [link.hashtag.display_name for link in story.hashtags.all()], "mentions": [compact_user(link.user, viewer) for link in story.mentions.all()], "view_count": story.views.count(), "viewer_has_viewed": StoryView.objects.filter(story=story, viewer=viewer).exists(), "reaction": getattr(StoryReaction.objects.filter(story=story, user=viewer).first(), "reaction", None), "poll": poll_data}


def reel_payload(reel, viewer):
    return {"id": str(reel.id), "author": compact_user(reel.author, viewer), "caption": reel.caption, "audience": reel.audience if reel.author == viewer else None, "comments_enabled": reel.comments_enabled, "status": reel.status, "processing_status": reel.processing_status, "location_name": reel.location_name, "video_url": reel.video.url if reel.video else reel.video_url, "thumbnail_url": reel.cover_image.url if reel.cover_image else reel.thumbnail_url, "duration": reel.duration, "width": reel.width, "height": reel.height, "aspect_ratio": reel.aspect_ratio, "view_count": reel.view_count, "share_count": reel.share_count, "published_at": reel.published_at.isoformat() if reel.published_at else None, "hashtags": [link.hashtag.display_name for link in reel.hashtags.all()], "mentions": [compact_user(link.user, viewer) for link in reel.mentions.all()], "tagged_users": [compact_user(link.user, viewer) for link in reel.tagged_users.all()], "like_count": getattr(reel, "like_total", reel.likes.count()), "comment_count": getattr(reel, "comment_total", reel.comments.filter(is_deleted=False).count()), "viewer_has_liked": ReelLike.objects.filter(reel=reel, user=viewer).exists(), "viewer_has_saved": SavedReel.objects.filter(reel=reel, user=viewer).exists(), "permissions": {"can_edit": reel.author == viewer, "can_delete": reel.author == viewer, "can_archive": reel.author == viewer, "can_comment": reel.comments_enabled and can_access_reel(viewer, reel)}}


@method_decorator(csrf_exempt, name="dispatch")
class StoryCollectionView(AuthenticatedView):
    def post(self, request):
        try:
            story = create_story(request.user_obj, parse_payload(request), request.FILES.get("media"))
            return response(True, "Story created successfully.", {"story": story_payload(story, request.user_obj)}, status=201)
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except ValueError as exc:
            return response(False, str(exc), status=400)


@method_decorator(csrf_exempt, name="dispatch")
class StoryTrayView(AuthenticatedView):
    def get(self, request):
        expire_stories()
        qs = visible_stories_for(request.user_obj)
        return response(True, "Story tray loaded.", page(request, qs, lambda story: story_payload(story, request.user_obj)))


@method_decorator(csrf_exempt, name="dispatch")
class StoryDetailView(AuthenticatedView):
    def get(self, request, story_id):
        try:
            story = Story.objects.get(id=story_id)
            if not can_access_story(request.user_obj, story):
                return response(False, "Story is not available.", status=403)
            return response(True, "Story loaded successfully.", {"story": story_payload(story, request.user_obj)})
        except Story.DoesNotExist:
            return response(False, "Story was not found.", status=404)

    def delete(self, request, story_id):
        story = Story.objects.get(id=story_id)
        if story.author != request.user_obj:
            return response(False, "Only the story owner can delete this story.", status=403)
        story.status = Story.STATUS_DELETED
        story.deleted_at = timezone.now()
        story.save(update_fields=["status", "deleted_at", "updated_at"])
        return response(True, "Story deleted successfully.")


@method_decorator(csrf_exempt, name="dispatch")
class StoryViewView(AuthenticatedView):
    def post(self, request, story_id):
        story = Story.objects.get(id=story_id)
        if not can_access_story(request.user_obj, story):
            return response(False, "Story is not available.", status=403)
        if story.author != request.user_obj:
            StoryView.objects.get_or_create(story=story, viewer=request.user_obj)
        return response(True, "Story view recorded.", {"view_count": story.views.count()})


@method_decorator(csrf_exempt, name="dispatch")
class StoryViewersView(AuthenticatedView):
    def get(self, request, story_id):
        story = Story.objects.get(id=story_id)
        if story.author != request.user_obj and not request.user_obj.is_staff:
            return response(False, "Only the story owner can view viewers.", status=403)
        qs = StoryView.objects.filter(story=story).select_related("viewer").order_by("-created_at")
        return response(True, "Story viewers loaded.", page(request, qs, lambda view: compact_user(view.viewer, request.user_obj)))


@method_decorator(csrf_exempt, name="dispatch")
class StoryReactionView(AuthenticatedView):
    def post(self, request, story_id):
        story = Story.objects.get(id=story_id)
        if not can_access_story(request.user_obj, story):
            return response(False, "Story is not available.", status=403)
        reaction = body(request).get("reaction", "like")
        obj, _ = StoryReaction.objects.update_or_create(story=story, user=request.user_obj, defaults={"reaction": reaction})
        create_notification(story.author, request.user_obj, "story_reaction", message="Your story received a reaction.")
        return response(True, "Story reaction updated.", {"reaction": obj.reaction})

    def delete(self, request, story_id):
        StoryReaction.objects.filter(story_id=story_id, user=request.user_obj).delete()
        return response(True, "Story reaction removed.")


@method_decorator(csrf_exempt, name="dispatch")
class StoryReplyView(AuthenticatedView):
    def post(self, request, story_id):
        story = Story.objects.get(id=story_id)
        if not can_access_story(request.user_obj, story):
            return response(False, "Story is not available.", status=403)
        if not story.replies_enabled:
            return response(False, "Replies are disabled for this story.", status=403)
        reply = StoryReply.objects.create(story=story, author=request.user_obj, text=clean_text(body(request).get("text", ""), 1000))
        create_notification(story.author, request.user_obj, "story_reply", message="Your story has a new reply.")
        return response(True, "Story reply sent.", {"reply_id": str(reply.id)}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class StoryReportView(AuthenticatedView):
    def post(self, request, story_id):
        story = Story.objects.get(id=story_id)
        if not can_access_story(request.user_obj, story):
            return response(False, "Story is not available.", status=403)
        payload = body(request)
        report, _ = StoryReport.objects.get_or_create(story=story, reporter=request.user_obj, reason=payload.get("reason", "other"), defaults={"details": clean_text(payload.get("details", ""), 1000)})
        return response(True, "Story report submitted.", {"report_id": report.id})


@method_decorator(csrf_exempt, name="dispatch")
class StoryPollVoteView(AuthenticatedView):
    def post(self, request, story_id):
        story = Story.objects.get(id=story_id)
        if not can_access_story(request.user_obj, story):
            return response(False, "Story is not available.", status=403)
        option = StoryPollOption.objects.get(id=body(request).get("option_id"), poll=story.poll)
        StoryPollVote.objects.update_or_create(poll=story.poll, voter=request.user_obj, defaults={"option": option})
        return response(True, "Poll vote recorded.", {"poll": story_payload(story, request.user_obj)["poll"]})

    def delete(self, request, story_id):
        story = Story.objects.get(id=story_id)
        StoryPollVote.objects.filter(poll=story.poll, voter=request.user_obj).delete()
        return response(True, "Poll vote removed.")


@method_decorator(csrf_exempt, name="dispatch")
class HighlightListView(AuthenticatedView):
    def get(self, request, username):
        owner = get_user_model().objects.get(username__iexact=username)
        qs = StoryHighlight.objects.filter(owner=owner).order_by("display_order", "created_at")
        return response(True, "Highlights loaded.", page(request, qs, lambda h: {"id": str(h.id), "title": h.title, "cover_image": h.cover_image.url if h.cover_image else None, "story_count": h.items.count()}))


@method_decorator(csrf_exempt, name="dispatch")
class HighlightView(AuthenticatedView):
    def post(self, request):
        payload = body(request)
        h = StoryHighlight.objects.create(owner=request.user_obj, title=clean_text(payload.get("title", "Highlight"), 60), display_order=int(payload.get("display_order", 0)))
        return response(True, "Highlight created.", {"highlight_id": str(h.id)}, status=201)

    def patch(self, request, highlight_id):
        h = StoryHighlight.objects.get(id=highlight_id, owner=request.user_obj)
        payload = body(request)
        if "title" in payload:
            h.title = clean_text(payload["title"], 60)
        if "display_order" in payload:
            h.display_order = int(payload["display_order"])
        h.save()
        return response(True, "Highlight updated.", {"highlight_id": str(h.id)})

    def delete(self, request, highlight_id):
        StoryHighlight.objects.filter(id=highlight_id, owner=request.user_obj).delete()
        return response(True, "Highlight deleted.")


@method_decorator(csrf_exempt, name="dispatch")
class HighlightStoryView(AuthenticatedView):
    def post(self, request, highlight_id):
        h = StoryHighlight.objects.get(id=highlight_id, owner=request.user_obj)
        story = Story.objects.get(id=body(request).get("story_id"), author=request.user_obj)
        item, _ = StoryHighlightItem.objects.get_or_create(highlight=h, story=story, defaults={"display_order": h.items.count()})
        return response(True, "Story added to highlight.", {"item_id": item.id})

    def delete(self, request, highlight_id, story_id):
        StoryHighlightItem.objects.filter(highlight_id=highlight_id, highlight__owner=request.user_obj, story_id=story_id).delete()
        return response(True, "Story removed from highlight.")


@method_decorator(csrf_exempt, name="dispatch")
class ReelCollectionView(AuthenticatedView):
    def post(self, request):
        try:
            reel = create_reel(request.user_obj, parse_payload(request), request.FILES.get("video"), request.FILES.get("cover"))
            return response(True, "Reel created successfully.", {"reel": reel_payload(reel, request.user_obj)}, status=201)
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except ValueError as exc:
            return response(False, str(exc), status=400)


@method_decorator(csrf_exempt, name="dispatch")
class ReelFeedView(AuthenticatedView):
    def get(self, request):
        cursor = request.GET.get("cursor")
        qs = visible_reels_for(request.user_obj)
        if cursor:
            qs = qs.filter(published_at__lt=cursor.replace(" ", "+"))
        limit = min(max(int(request.GET.get("limit", 10)), 1), 30)
        reels = list(qs[:limit + 1])
        next_cursor = reels[-1].published_at.isoformat() if len(reels) > limit and reels[-1].published_at else None
        return response(True, "Reel feed loaded.", {"results": [reel_payload(r, request.user_obj) for r in reels[:limit]], "next_cursor": next_cursor})


@method_decorator(csrf_exempt, name="dispatch")
class ReelDetailView(AuthenticatedView):
    def get(self, request, reel_id):
        reel = Reel.objects.get(id=reel_id)
        if not can_access_reel(request.user_obj, reel):
            return response(False, "Reel is not available.", status=403)
        return response(True, "Reel loaded.", {"reel": reel_payload(reel, request.user_obj)})

    def patch(self, request, reel_id):
        reel = Reel.objects.get(id=reel_id)
        if reel.author != request.user_obj:
            return response(False, "Only the reel owner can edit this reel.", status=403)
        payload = body(request)
        for field, limit in [("caption", 2200), ("location_name", 140)]:
            if field in payload:
                setattr(reel, field, clean_text(payload[field], limit))
        for field in ["audience", "comments_enabled"]:
            if field in payload:
                setattr(reel, field, payload[field])
        reel.save()
        return response(True, "Reel updated.", {"reel": reel_payload(reel, request.user_obj)})

    def delete(self, request, reel_id):
        reel = Reel.objects.get(id=reel_id)
        if reel.author != request.user_obj:
            return response(False, "Only the reel owner can delete this reel.", status=403)
        reel.status = Reel.STATUS_DELETED
        reel.deleted_at = timezone.now()
        reel.save(update_fields=["status", "deleted_at", "updated_at"])
        return response(True, "Reel deleted.")


@method_decorator(csrf_exempt, name="dispatch")
class ReelSimpleActionView(AuthenticatedView):
    def post(self, request, reel_id, action):
        reel = Reel.objects.get(id=reel_id)
        if action in {"like", "save", "view", "share", "report", "hide", "not-interested"} and not can_access_reel(request.user_obj, reel):
            return response(False, "Reel is not available.", status=403)
        if action == "like":
            ReelLike.objects.get_or_create(reel=reel, user=request.user_obj)
            create_notification(reel.author, request.user_obj, "reel_liked", message="Your reel was liked.")
            return response(True, "Reel liked.", {"liked": True, "like_count": reel.likes.count()})
        if action == "save":
            SavedReel.objects.get_or_create(reel=reel, user=request.user_obj)
            return response(True, "Reel saved.", {"saved": True})
        if action == "view":
            payload = body(request)
            duration = float(payload.get("watch_duration", 0) or 0)
            complete = float(payload.get("completion_percentage", 0) or 0) >= 90
            if reel.author != request.user_obj and duration >= REEL_VIEW_THRESHOLD_SECONDS:
                obj, created = ReelView.objects.update_or_create(reel=reel, viewer=request.user_obj, defaults={"watch_duration": duration, "completion_percentage": payload.get("completion_percentage", 0), "completed": complete})
                if created:
                    reel.view_count += 1
                    reel.save(update_fields=["view_count", "updated_at"])
            return response(True, "Reel view recorded.", {"view_count": reel.view_count})
        if action == "share":
            reel.share_count += 1
            reel.save(update_fields=["share_count", "updated_at"])
            return response(True, "Reel share recorded.", {"share_count": reel.share_count})
        if action == "report":
            payload = body(request)
            report, _ = ReelReport.objects.get_or_create(reel=reel, reporter=request.user_obj, reason=payload.get("reason", "other"), defaults={"details": clean_text(payload.get("details", ""), 1000)})
            return response(True, "Reel report submitted.", {"report_id": report.id})
        if action == "hide":
            HiddenReel.objects.get_or_create(reel=reel, user=request.user_obj)
            return response(True, "Reel hidden.")
        if action == "not-interested":
            ReelNotInterested.objects.get_or_create(reel=reel, user=request.user_obj)
            return response(True, "Preference recorded.")
        if action in {"archive", "restore"}:
            if reel.author != request.user_obj:
                return response(False, "Only the reel owner can change archive state.", status=403)
            reel.status = Reel.STATUS_ARCHIVED if action == "archive" else Reel.STATUS_PUBLISHED
            reel.archived_at = timezone.now() if action == "archive" else None
            reel.save()
            return response(True, f"Reel {action}d.", {"reel": reel_payload(reel, request.user_obj)})
        return response(False, "Unknown reel action.", status=400)

    def delete(self, request, reel_id, action):
        reel = Reel.objects.get(id=reel_id)
        if action == "like":
            ReelLike.objects.filter(reel=reel, user=request.user_obj).delete()
            return response(True, "Reel unliked.", {"liked": False, "like_count": reel.likes.count()})
        if action == "save":
            SavedReel.objects.filter(reel=reel, user=request.user_obj).delete()
            return response(True, "Reel unsaved.", {"saved": False})
        return response(False, "Unknown reel action.", status=400)


@method_decorator(csrf_exempt, name="dispatch")
class ReelCommentsView(AuthenticatedView):
    def get(self, request, reel_id):
        reel = Reel.objects.get(id=reel_id)
        if not can_access_reel(request.user_obj, reel):
            return response(False, "Reel is not available.", status=403)
        qs = ReelComment.objects.filter(reel=reel, parent__isnull=True).select_related("author").order_by("-created_at")
        return response(True, "Reel comments loaded.", page(request, qs, lambda c: {"id": str(c.id), "author": compact_user(c.author, request.user_obj), "text": "" if c.is_deleted else c.text, "parent_id": str(c.parent_id) if c.parent_id else None}))

    def post(self, request, reel_id):
        reel = Reel.objects.get(id=reel_id)
        if not can_access_reel(request.user_obj, reel):
            return response(False, "Reel is not available.", status=403)
        if not reel.comments_enabled:
            return response(False, "Comments are disabled for this reel.", status=403)
        payload = body(request)
        parent = ReelComment.objects.filter(id=payload.get("parent_id"), reel=reel).first() if payload.get("parent_id") else None
        if parent and parent.parent_id:
            return response(False, "Reply nesting is limited to one level.", status=400)
        comment = ReelComment.objects.create(reel=reel, author=request.user_obj, parent=parent, text=clean_text(payload.get("text", ""), 1000))
        create_notification(reel.author, request.user_obj, "reel_commented", message="Your reel has a new comment.")
        return response(True, "Reel comment created.", {"comment_id": str(comment.id)}, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class ReelListsView(AuthenticatedView):
    def get(self, request, list_name=None, username=None, hashtag=None):
        if list_name == "saved":
            ids = SavedReel.objects.filter(user=request.user_obj).values_list("reel_id", flat=True)
            qs = visible_reels_for(request.user_obj).filter(id__in=ids)
        elif list_name == "drafts":
            qs = Reel.objects.filter(author=request.user_obj, status=Reel.STATUS_DRAFT).order_by("-created_at")
        elif list_name == "archived":
            qs = Reel.objects.filter(author=request.user_obj, status=Reel.STATUS_ARCHIVED).order_by("-archived_at")
        elif username:
            author = get_user_model().objects.get(username__iexact=username)
            qs = visible_reels_for(request.user_obj).filter(author=author)
        elif hashtag:
            qs = visible_reels_for(request.user_obj).filter(hashtags__hashtag__name=hashtag.lower())
        else:
            qs = visible_reels_for(request.user_obj)
        return response(True, "Reels loaded.", page(request, qs, lambda r: reel_payload(r, request.user_obj)))


@method_decorator(csrf_exempt, name="dispatch")
class AdminStoryReelView(AuthenticatedView):
    def _staff(self, request):
        if not request.user_obj.is_staff:
            raise PermissionError("Staff access is required.")

    def get(self, request, kind):
        try:
            self._staff(request)
            if kind == "stories":
                qs = Story.objects.all().select_related("author").order_by("-created_at")
                return response(True, "Admin stories loaded.", page(request, qs, lambda s: story_payload(s, request.user_obj)))
            qs = Reel.objects.all().select_related("author").order_by("-created_at")
            status = request.GET.get("status")
            processing = request.GET.get("processing_status")
            if status:
                qs = qs.filter(status=status)
            if processing:
                qs = qs.filter(processing_status=processing)
            return response(True, "Admin reels loaded.", page(request, qs, lambda r: reel_payload(r, request.user_obj)))
        except PermissionError as exc:
            return response(False, str(exc), status=403)

    def post(self, request, kind, item_id, action):
        try:
            self._staff(request)
            model = Story if kind == "stories" else Reel
            obj = model.objects.get(id=item_id)
            if action == "remove":
                obj.status = Story.STATUS_REMOVED if kind == "stories" else Reel.STATUS_REMOVED
            elif action == "restore":
                obj.status = Story.STATUS_PUBLISHED if kind == "stories" else Reel.STATUS_PUBLISHED
            elif action == "retry-processing" and kind == "reels":
                obj.processing_status = Reel.PROCESSING_PENDING
            else:
                return response(False, "Unknown moderation action.", status=400)
            obj.save()
            AdminAuditLog.objects.create(admin_user=request.user_obj, action=f"{kind}_{action}", target=str(obj.id), reason=body(request).get("reason", ""))
            return response(True, "Moderation action recorded.")
        except PermissionError as exc:
            return response(False, str(exc), status=403)
