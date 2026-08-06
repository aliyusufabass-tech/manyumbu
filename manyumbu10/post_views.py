import json
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import QueryDict
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import Comment, CommentLike, HiddenPost, Notification, Post, PostLike, PostReport, SavedPost
from .post_services import can_access_post, clean_text, create_notification, create_post, edit_post, visible_posts_for
from .profile_views import AuthenticatedView, compact_user, current_user, page
from .views import body, response
from .storage import absolute_media_url


def parse_payload(request):
    if request.content_type and request.content_type.startswith("multipart/"):
        payload = request.POST.dict()
        for key in ["hashtags", "mentions", "tagged_users", "selected_users"]:
            if key in payload:
                try:
                    payload[key] = json.loads(payload[key])
                except Exception:
                    payload[key] = [item.strip() for item in payload[key].split(",") if item.strip()]
        return payload
    return body(request)


def post_queryset():
    return Post.objects.select_related("author", "author__profile").prefetch_related("media", "hashtags__hashtag", "tagged_users__user", "mentions__user")


def media_payload(media):
    url = absolute_media_url(media.file) or media.media_url
    return {
        "id": str(media.id),
        "url": url,
        "secure_url": media.secure_url or url,
        "media_type": media.media_type,
        "width": media.width,
        "height": media.height,
        "duration": media.duration,
        "file_size": media.file_size,
        "display_order": media.display_order,
        "thumbnail": absolute_media_url(media.thumbnail),
        "upload_provider_id": media.upload_provider_id,
        "created_at": media.created_at.isoformat(),
    }


def post_payload(post, viewer):
    liked = PostLike.objects.filter(post=post, user=viewer).exists()
    saved = SavedPost.objects.filter(post=post, user=viewer).exists()
    return {
        "id": str(post.id),
        "author": compact_user(post.author, viewer),
        "caption": post.caption,
        "post_type": post.post_type,
        "audience": post.audience if post.author == viewer else None,
        "comments_enabled": post.comments_enabled,
        "status": post.status,
        "location_name": post.location_name,
        "is_edited": post.is_edited,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat(),
        "media": [media_payload(item) for item in post.media.all().order_by("display_order")],
        "hashtags": [link.hashtag.display_name for link in post.hashtags.all()],
        "tagged_users": [compact_user(link.user, viewer) for link in post.tagged_users.all()],
        "mentions": [compact_user(link.user, viewer) for link in post.mentions.all()],
        "like_count": getattr(post, "like_total", post.likes.count()),
        "comment_count": getattr(post, "comment_total", post.comments.filter(is_deleted=False).count()),
        "share_count": post.share_count,
        "viewer_has_liked": liked,
        "viewer_has_saved": saved,
        "permissions": {
            "can_edit": post.author == viewer,
            "can_delete": post.author == viewer,
            "can_archive": post.author == viewer,
            "can_comment": post.comments_enabled and can_access_post(viewer, post),
            "can_like": can_access_post(viewer, post),
            "can_save": can_access_post(viewer, post),
        },
    }


def comment_payload(comment, viewer):
    return {
        "id": str(comment.id),
        "post_id": str(comment.post_id),
        "author": compact_user(comment.author, viewer),
        "parent_id": str(comment.parent_id) if comment.parent_id else None,
        "text": "" if comment.is_deleted else comment.text,
        "is_edited": comment.is_edited,
        "is_deleted": comment.is_deleted,
        "like_count": comment.likes.count(),
        "viewer_has_liked": CommentLike.objects.filter(comment=comment, user=viewer).exists(),
        "created_at": comment.created_at.isoformat(),
        "updated_at": comment.updated_at.isoformat(),
    }


@method_decorator(csrf_exempt, name="dispatch")
class PostCollectionView(AuthenticatedView):
    def post(self, request):
        try:
            payload = parse_payload(request)
            post = create_post(request.user_obj, payload, request.FILES.getlist("media"))
            return response(True, "Post created successfully.", {"post": post_payload(post, request.user_obj)}, status=201)
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except (ValueError, IntegrityError) as exc:
            return response(False, str(exc), status=400)


@method_decorator(csrf_exempt, name="dispatch")
class PostDetailView(AuthenticatedView):
    def get(self, request, post_id):
        try:
            post = post_queryset().get(id=post_id)
            if not can_access_post(request.user_obj, post):
                return response(False, "Post is not available.", status=403)
            return response(True, "Post loaded successfully.", {"post": post_payload(post, request.user_obj)})
        except Post.DoesNotExist:
            return response(False, "Post was not found.", status=404)

    def patch(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            post = edit_post(post, request.user_obj, parse_payload(request))
            return response(True, "Post updated successfully.", {"post": post_payload(post, request.user_obj)})
        except Post.DoesNotExist:
            return response(False, "Post was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except ValueError as exc:
            return response(False, str(exc), status=400)

    def delete(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            if post.author != request.user_obj:
                return response(False, "Only the post owner can delete this post.", status=403)
            post.status = Post.STATUS_DELETED
            post.deleted_at = timezone.now()
            post.save(update_fields=["status", "deleted_at", "updated_at"])
            return response(True, "Post deleted successfully.")
        except Post.DoesNotExist:
            return response(False, "Post was not found.", status=404)


@method_decorator(csrf_exempt, name="dispatch")
class PostArchiveView(AuthenticatedView):
    def post(self, request, post_id, action):
        try:
            post = Post.objects.get(id=post_id)
            if post.author != request.user_obj:
                return response(False, "Only the post owner can change archive state.", status=403)
            if action == "archive":
                post.status = Post.STATUS_ARCHIVED
                post.archived_at = timezone.now()
                message = "Post archived successfully."
            elif action == "restore":
                post.status = Post.STATUS_PUBLISHED
                post.archived_at = None
                if not post.published_at:
                    post.published_at = timezone.now()
                message = "Post restored successfully."
            else:
                return response(False, "Unknown archive action.", status=400)
            post.save()
            return response(True, message, {"post": post_payload(post, request.user_obj)})
        except Post.DoesNotExist:
            return response(False, "Post was not found.", status=404)


@method_decorator(csrf_exempt, name="dispatch")
class PostLikeView(AuthenticatedView):
    def post(self, request, post_id):
        post = Post.objects.get(id=post_id)
        if not can_access_post(request.user_obj, post):
            return response(False, "Post is not available.", status=403)
        PostLike.objects.get_or_create(post=post, user=request.user_obj)
        create_notification(post.author, request.user_obj, Notification.TYPE_POST_LIKED, post=post, message="Your post was liked.")
        return response(True, "Post liked successfully.", {"liked": True, "like_count": post.likes.count()})

    def delete(self, request, post_id):
        post = Post.objects.get(id=post_id)
        PostLike.objects.filter(post=post, user=request.user_obj).delete()
        return response(True, "Post unliked successfully.", {"liked": False, "like_count": post.likes.count()})


@method_decorator(csrf_exempt, name="dispatch")
class PostSaveView(AuthenticatedView):
    def post(self, request, post_id):
        post = Post.objects.get(id=post_id)
        if not can_access_post(request.user_obj, post):
            return response(False, "Post is not available.", status=403)
        SavedPost.objects.get_or_create(post=post, user=request.user_obj)
        return response(True, "Post saved successfully.", {"saved": True})

    def delete(self, request, post_id):
        post = Post.objects.get(id=post_id)
        SavedPost.objects.filter(post=post, user=request.user_obj).delete()
        return response(True, "Post unsaved successfully.", {"saved": False})


@method_decorator(csrf_exempt, name="dispatch")
class PostLikesListView(AuthenticatedView):
    def get(self, request, post_id):
        post = Post.objects.get(id=post_id)
        if not can_access_post(request.user_obj, post):
            return response(False, "Post is not available.", status=403)
        qs = PostLike.objects.filter(post=post).select_related("user").order_by("-created_at")
        return response(True, "Post likes loaded.", page(request, qs, lambda like: compact_user(like.user, request.user_obj)))


@method_decorator(csrf_exempt, name="dispatch")
class PostCommentsView(AuthenticatedView):
    def get(self, request, post_id):
        post = Post.objects.get(id=post_id)
        if not can_access_post(request.user_obj, post):
            return response(False, "Post is not available.", status=403)
        sort = request.GET.get("sort", "newest")
        qs = Comment.objects.filter(post=post, parent__isnull=True).select_related("author").order_by("-created_at" if sort == "newest" else "created_at")
        return response(True, "Comments loaded.", page(request, qs, lambda comment: comment_payload(comment, request.user_obj)))

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            if not can_access_post(request.user_obj, post):
                return response(False, "Post is not available.", status=403)
            if not post.comments_enabled:
                return response(False, "Comments are disabled for this post.", status=403)
            payload = body(request)
            parent = None
            if payload.get("parent_id"):
                parent = Comment.objects.get(id=payload["parent_id"], post=post)
                if parent.parent_id:
                    return response(False, "Reply nesting is limited to one level.", status=400)
            comment = Comment.objects.create(post=post, author=request.user_obj, parent=parent, text=clean_text(payload.get("text", ""), 1000))
            create_notification(post.author, request.user_obj, Notification.TYPE_POST_COMMENTED, post=post, comment=comment, message="Your post has a new comment.")
            if parent:
                create_notification(parent.author, request.user_obj, Notification.TYPE_COMMENT_REPLIED, post=post, comment=comment, message="Your comment has a new reply.")
            return response(True, "Comment created successfully.", {"comment": comment_payload(comment, request.user_obj)}, status=201)
        except (ValueError, Comment.DoesNotExist) as exc:
            return response(False, str(exc), status=400)


@method_decorator(csrf_exempt, name="dispatch")
class CommentDetailView(AuthenticatedView):
    def patch(self, request, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id)
            if comment.author != request.user_obj:
                return response(False, "Only the comment owner can edit this comment.", status=403)
            comment.text = clean_text(body(request).get("text", ""), 1000)
            comment.is_edited = True
            comment.save(update_fields=["text", "is_edited", "updated_at"])
            return response(True, "Comment updated successfully.", {"comment": comment_payload(comment, request.user_obj)})
        except Comment.DoesNotExist:
            return response(False, "Comment was not found.", status=404)
        except ValueError as exc:
            return response(False, str(exc), status=400)

    def delete(self, request, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id)
            if comment.author != request.user_obj:
                return response(False, "Only the comment owner can delete this comment.", status=403)
            comment.is_deleted = True
            comment.save(update_fields=["is_deleted", "updated_at"])
            return response(True, "Comment deleted successfully.")
        except Comment.DoesNotExist:
            return response(False, "Comment was not found.", status=404)


@method_decorator(csrf_exempt, name="dispatch")
class CommentLikeView(AuthenticatedView):
    def post(self, request, comment_id):
        comment = Comment.objects.select_related("post", "author").get(id=comment_id)
        if not can_access_post(request.user_obj, comment.post):
            return response(False, "Comment is not available.", status=403)
        CommentLike.objects.get_or_create(comment=comment, user=request.user_obj)
        create_notification(comment.author, request.user_obj, Notification.TYPE_COMMENT_LIKED, post=comment.post, comment=comment, message="Your comment was liked.")
        return response(True, "Comment liked successfully.", {"liked": True, "like_count": comment.likes.count()})

    def delete(self, request, comment_id):
        comment = Comment.objects.get(id=comment_id)
        CommentLike.objects.filter(comment=comment, user=request.user_obj).delete()
        return response(True, "Comment unliked successfully.", {"liked": False, "like_count": comment.likes.count()})


@method_decorator(csrf_exempt, name="dispatch")
class FeedView(AuthenticatedView):
    def get(self, request):
        cursor = request.GET.get("cursor")
        qs = visible_posts_for(request.user_obj)
        if cursor:
            parsed_cursor = parse_datetime(cursor.replace(" ", "+")) or parse_datetime(cursor)
            if parsed_cursor:
                qs = qs.filter(published_at__lt=parsed_cursor)
        limit = min(max(int(request.GET.get("limit", 10)), 1), 30)
        posts = list(qs[:limit + 1])
        next_cursor = posts[-1].published_at.isoformat() if len(posts) > limit and posts[-1].published_at else None
        posts = posts[:limit]
        return response(True, "Feed loaded successfully.", {"results": [post_payload(post, request.user_obj) for post in posts], "next_cursor": next_cursor})


@method_decorator(csrf_exempt, name="dispatch")
class UserPostsView(AuthenticatedView):
    def get(self, request, username):
        author = get_user_model().objects.get(username__iexact=username)
        qs = visible_posts_for(request.user_obj).filter(author=author)
        return response(True, "User posts loaded.", page(request, qs, lambda post: post_payload(post, request.user_obj)))


@method_decorator(csrf_exempt, name="dispatch")
class SavedPostsView(AuthenticatedView):
    def get(self, request):
        saved_ids = SavedPost.objects.filter(user=request.user_obj).values_list("post_id", flat=True)
        qs = visible_posts_for(request.user_obj).filter(id__in=saved_ids)
        return response(True, "Saved posts loaded.", page(request, qs, lambda post: post_payload(post, request.user_obj)))


@method_decorator(csrf_exempt, name="dispatch")
class ArchivedPostsView(AuthenticatedView):
    def get(self, request):
        qs = post_queryset().filter(author=request.user_obj, status=Post.STATUS_ARCHIVED).order_by("-archived_at")
        return response(True, "Archived posts loaded.", page(request, qs, lambda post: post_payload(post, request.user_obj)))


@method_decorator(csrf_exempt, name="dispatch")
class HashtagPostsView(AuthenticatedView):
    def get(self, request, hashtag):
        qs = visible_posts_for(request.user_obj).filter(hashtags__hashtag__name=hashtag.lower())
        return response(True, "Hashtag posts loaded.", page(request, qs, lambda post: post_payload(post, request.user_obj)))


@method_decorator(csrf_exempt, name="dispatch")
class PostReportView(AuthenticatedView):
    def post(self, request, post_id):
        post = Post.objects.get(id=post_id)
        if not can_access_post(request.user_obj, post):
            return response(False, "Post is not available.", status=403)
        payload = body(request)
        report, _ = PostReport.objects.get_or_create(post=post, reporter=request.user_obj, reason=payload.get("reason", "other"), defaults={"details": clean_text(payload.get("details", ""), 1000)})
        return response(True, "Post report submitted successfully.", {"report_id": report.id})


@method_decorator(csrf_exempt, name="dispatch")
class PostHideView(AuthenticatedView):
    def post(self, request, post_id):
        post = Post.objects.get(id=post_id)
        HiddenPost.objects.get_or_create(post=post, user=request.user_obj)
        return response(True, "Post hidden from your feed.")


@method_decorator(csrf_exempt, name="dispatch")
class AdminPostManagementView(AuthenticatedView):
    def dispatch(self, request, *args, **kwargs):
        auth_response = super().dispatch(request, *args, **kwargs)
        return auth_response

    def _require_staff(self, request):
        if not request.user_obj.is_staff:
            raise PermissionError("Staff access is required.")

    def get(self, request, post_id=None):
        try:
            self._require_staff(request)
            if post_id:
                post = post_queryset().get(id=post_id)
                return response(True, "Admin post detail loaded.", {"post": post_payload(post, request.user_obj), "reports": post.reports.count()})
            qs = post_queryset().all().order_by("-created_at")
            status = request.GET.get("status")
            author = request.GET.get("author")
            media_type = request.GET.get("media_type")
            q = request.GET.get("q")
            if status:
                qs = qs.filter(status=status)
            if author:
                qs = qs.filter(author__username__icontains=author)
            if media_type:
                qs = qs.filter(media__media_type=media_type).distinct()
            if q:
                qs = qs.filter(Q(caption__icontains=q) | Q(author__username__icontains=q)).distinct()
            return response(True, "Admin posts loaded.", page(request, qs, lambda post: post_payload(post, request.user_obj)))
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except Post.DoesNotExist:
            return response(False, "Post was not found.", status=404)

    def post(self, request, post_id, action):
        try:
            self._require_staff(request)
            post = Post.objects.get(id=post_id)
            payload = body(request)
            if action == "remove":
                post.status = Post.STATUS_REMOVED
                message = "Post removed by moderation."
            elif action == "restore":
                post.status = Post.STATUS_PUBLISHED
                if not post.published_at:
                    post.published_at = timezone.now()
                message = "Post restored by moderation."
            else:
                return response(False, "Unknown moderation action.", status=400)
            post.save(update_fields=["status", "published_at", "updated_at"])
            from .models import AdminAuditLog
            AdminAuditLog.objects.create(admin_user=request.user_obj, action=f"post_{action}", target=str(post.id), reason=payload.get("reason", ""))
            return response(True, message, {"post": post_payload(post, request.user_obj)})
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except Post.DoesNotExist:
            return response(False, "Post was not found.", status=404)
