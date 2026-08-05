import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import BlockedUser, CloseFriend, Follow, FollowRequest, MutedUser, RestrictedUser, UserPrivacySettings, normalize_phone_number
from .services import (
    accept_follow_request,
    block_user,
    can_view_profile,
    cancel_follow_request,
    decode_token,
    ensure_profile_records,
    follow_or_request,
    is_following,
    reject_follow_request,
    remove_follower,
    unblock_user,
    unfollow_user,
    users_blocked_between,
)
from .views import body, public_user, response


def current_user(request):
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.startswith("Bearer "):
        raise PermissionError("Authentication credentials were not provided.")
    payload = decode_token(header.removeprefix("Bearer ").strip(), expected_type="access")
    user = get_user_model().objects.get(phone_number=payload["sub"], is_active=True, is_email_verified=True)
    ensure_profile_records(user)
    return user


def get_target(phone_or_username):
    User = get_user_model()
    try:
        phone = normalize_phone_number(phone_or_username)
        return User.objects.get(phone_number=phone)
    except Exception:
        return User.objects.get(username__iexact=phone_or_username)


def page(request, queryset, serializer, default_size=20):
    try:
        limit = min(max(int(request.GET.get("limit", default_size)), 1), 50)
        offset = max(int(request.GET.get("offset", 0)), 0)
    except ValueError:
        limit, offset = default_size, 0
    total = queryset.count()
    rows = [serializer(item) for item in queryset[offset:offset + limit]]
    return {"results": rows, "count": total, "next_offset": offset + limit if offset + limit < total else None}


def profile_payload(user, viewer=None, include_private=False):
    ensure_profile_records(user)
    profile = user.profile
    privacy = user.privacy_settings
    allowed = include_private or can_view_profile(viewer, user)
    data = {
        "username": user.username,
        "full_name": user.full_name,
        "profile_picture": user.profile_picture.url if user.profile_picture else None,
        "cover_photo": profile.cover_photo.url if profile.cover_photo else None,
        "bio": profile.bio if allowed else "",
        "website": profile.website if allowed and privacy.profile_details_public else "",
        "location": profile.location if allowed and privacy.profile_details_public else "",
        "date_joined": user.created_at.date().isoformat(),
        "account_type": profile.account_type,
        "is_verified": user.is_verified,
        "is_private": profile.is_private,
        "followers_count": user.follower_edges.count(),
        "following_count": user.following_edges.count(),
        "posts_count": profile.posts_count,
        "reels_count": profile.reels_count,
        "is_following": is_following(viewer, user) if viewer else False,
        "viewer_can_view_private_content": allowed,
        "mutual_followers_count": mutual_followers_count(viewer, user) if viewer and viewer != user else 0,
        "tabs": ["posts", "reels", "tagged", "saved"] if viewer == user else ["posts", "reels", "tagged"],
    }
    if include_private:
        data["phone_number"] = user.phone_number
        data["email"] = user.email
        data["date_of_birth"] = user.date_of_birth.isoformat()
    elif privacy.dob_visibility == UserPrivacySettings.DOB_FULL and allowed:
        data["date_of_birth"] = user.date_of_birth.isoformat()
    elif privacy.dob_visibility == UserPrivacySettings.DOB_MONTH_DAY and allowed:
        data["date_of_birth"] = user.date_of_birth.strftime("%m-%d")
    return data


def compact_user(user, viewer=None):
    ensure_profile_records(user)
    return {
        "username": user.username,
        "full_name": user.full_name,
        "profile_picture": user.profile_picture.url if user.profile_picture else None,
        "is_private": user.profile.is_private,
        "is_verified": user.is_verified,
        "is_following": is_following(viewer, user) if viewer else False,
        "mutual_followers_count": mutual_followers_count(viewer, user) if viewer and viewer != user else 0,
    }


def mutual_followers_count(viewer, target):
    if not viewer:
        return 0
    viewer_followers = Follow.objects.filter(following=viewer).values_list("follower_id", flat=True)
    return Follow.objects.filter(following=target, follower_id__in=viewer_followers).count()


class AuthenticatedView(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            request.user_obj = current_user(request)
        except Exception as exc:
            return response(False, str(exc), status=401)
        return super().dispatch(request, *args, **kwargs)


@method_decorator(csrf_exempt, name="dispatch")
class MeProfileView(AuthenticatedView):
    def get(self, request):
        return response(True, "Profile loaded successfully.", {"profile": profile_payload(request.user_obj, request.user_obj, include_private=True)})

    def patch(self, request):
        try:
            payload = body(request)
            user = request.user_obj
            ensure_profile_records(user)
            profile = user.profile
            if "username" in payload:
                username = payload["username"].strip().lower()
                if get_user_model().objects.exclude(phone_number=user.phone_number).filter(username=username).exists():
                    return response(False, "Username is already taken.", status=409)
                user.username = username
            for field in ["full_name"]:
                if field in payload:
                    setattr(user, field, payload[field].strip())
            for field in ["bio", "website", "location", "account_type"]:
                if field in payload:
                    setattr(profile, field, payload[field])
            if "is_private" in payload:
                became_public = profile.is_private and not bool(payload["is_private"])
                profile.is_private = bool(payload["is_private"])
                if became_public:
                    for req in FollowRequest.objects.filter(target=user, status=FollowRequest.STATUS_PENDING):
                        if not users_blocked_between(req.requester, user):
                            Follow.objects.get_or_create(follower=req.requester, following=user)
                            req.status = FollowRequest.STATUS_ACCEPTED
                            req.responded_at = __import__("django.utils.timezone").utils.timezone.now()
                            req.save(update_fields=["status", "responded_at", "updated_at"])
            user.full_clean(exclude=["password"])
            user.save()
            profile.save()
            return response(True, "Profile updated successfully.", {"profile": profile_payload(user, user, include_private=True)})
        except ValidationError as exc:
            return response(False, exc.messages, status=400)
        except ValueError as exc:
            return response(False, str(exc), status=400)


@method_decorator(csrf_exempt, name="dispatch")
class PublicProfileView(AuthenticatedView):
    def get(self, request, username):
        try:
            target = get_user_model().objects.get(username__iexact=username)
            if users_blocked_between(request.user_obj, target):
                return response(False, "Profile is not available.", status=403)
            return response(True, "Profile loaded successfully.", {"profile": profile_payload(target, request.user_obj)})
        except get_user_model().DoesNotExist:
            return response(False, "Profile was not found.", status=404)


@method_decorator(csrf_exempt, name="dispatch")
class PrivacySettingsView(AuthenticatedView):
    def get(self, request):
        settings = request.user_obj.privacy_settings
        return response(True, "Privacy settings loaded.", {"privacy": privacy_payload(settings)})

    def patch(self, request):
        payload = body(request)
        settings = request.user_obj.privacy_settings
        for field in ["show_in_suggestions", "phone_discoverable", "dob_visibility", "profile_details_public", "online_status_visible", "who_can_message_me", "who_can_add_to_conversations", "show_online_status", "show_last_seen", "send_read_receipts", "show_typing_indicator", "show_recording_indicator", "allow_message_requests", "allow_forwarded_messages_from_unknown_users", "who_can_call_me", "allow_voice_calls", "allow_video_calls", "show_call_notifications", "silence_calls_from_unknown_users"]:
            if field in payload:
                setattr(settings, field, payload[field])
        settings.full_clean()
        settings.save()
        return response(True, "Privacy settings updated successfully.", {"privacy": privacy_payload(settings)})


def privacy_payload(settings):
    return {
        "show_in_suggestions": settings.show_in_suggestions,
        "phone_discoverable": settings.phone_discoverable,
        "dob_visibility": settings.dob_visibility,
        "profile_details_public": settings.profile_details_public,
        "online_status_visible": settings.online_status_visible,
        "who_can_message_me": settings.who_can_message_me,
        "who_can_add_to_conversations": settings.who_can_add_to_conversations,
        "show_online_status": settings.show_online_status,
        "show_last_seen": settings.show_last_seen,
        "send_read_receipts": settings.send_read_receipts,
        "show_typing_indicator": settings.show_typing_indicator,
        "show_recording_indicator": settings.show_recording_indicator,
        "allow_message_requests": settings.allow_message_requests,
        "allow_forwarded_messages_from_unknown_users": settings.allow_forwarded_messages_from_unknown_users,
        "who_can_call_me": getattr(settings, "who_can_call_me", "everyone"),
        "allow_voice_calls": getattr(settings, "allow_voice_calls", True),
        "allow_video_calls": getattr(settings, "allow_video_calls", True),
        "show_call_notifications": getattr(settings, "show_call_notifications", True),
        "silence_calls_from_unknown_users": getattr(settings, "silence_calls_from_unknown_users", False),    }


@method_decorator(csrf_exempt, name="dispatch")
class SearchProfilesView(AuthenticatedView):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        User = get_user_model()
        blocked_ids = list(BlockedUser.objects.filter(Q(blocker=request.user_obj) | Q(blocked=request.user_obj)).values_list("blocker_id", "blocked_id"))
        hidden = {item for pair in blocked_ids for item in pair if item != request.user_obj.phone_number}
        queryset = User.objects.exclude(phone_number=request.user_obj.phone_number).exclude(phone_number__in=hidden).filter(is_active=True, is_email_verified=True)
        if q:
            phone_match = None
            try:
                phone_match = normalize_phone_number(q)
            except Exception:
                pass
            query = Q(username__icontains=q) | Q(full_name__icontains=q)
            if phone_match:
                query |= Q(phone_number=phone_match, privacy_settings__phone_discoverable=True)
            queryset = queryset.filter(query)
        return response(True, "Search results loaded.", page(request, queryset.order_by("username"), lambda user: compact_user(user, request.user_obj)))


@method_decorator(csrf_exempt, name="dispatch")
class FollowView(AuthenticatedView):
    def post(self, request, username):
        try:
            target = get_user_model().objects.get(username__iexact=username)
            state, obj = follow_or_request(request.user_obj, target)
            return response(True, "Follow action completed.", {"state": state, "request_id": getattr(obj, "id", None)})
        except get_user_model().DoesNotExist:
            return response(False, "User was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)
        except (ValueError, IntegrityError) as exc:
            return response(False, str(exc), status=400)

    def delete(self, request, username):
        target = get_user_model().objects.get(username__iexact=username)
        removed = unfollow_user(request.user_obj, target)
        return response(True, "Unfollowed successfully." if removed else "Follow relationship did not exist.", {"removed": removed})


@method_decorator(csrf_exempt, name="dispatch")
class FollowRequestActionView(AuthenticatedView):
    def post(self, request, request_id, action):
        try:
            if action == "accept":
                req = accept_follow_request(request.user_obj, request_id)
            elif action == "reject":
                req = reject_follow_request(request.user_obj, request_id)
            elif action == "cancel":
                req = cancel_follow_request(request.user_obj, request_id)
            else:
                return response(False, "Unknown request action.", status=400)
            return response(True, "Follow request updated successfully.", {"request": follow_request_payload(req)})
        except FollowRequest.DoesNotExist:
            return response(False, "Follow request was not found.", status=404)
        except PermissionError as exc:
            return response(False, str(exc), status=403)


def follow_request_payload(req):
    return {"id": req.id, "requester": compact_user(req.requester), "target": compact_user(req.target), "status": req.status, "created_at": req.created_at.isoformat()}


@method_decorator(csrf_exempt, name="dispatch")
class RelationshipListView(AuthenticatedView):
    def get(self, request, list_name):
        user = request.user_obj
        if list_name == "followers":
            qs = Follow.objects.filter(following=user).select_related("follower").order_by("-created_at")
            return response(True, "Followers loaded.", page(request, qs, lambda edge: compact_user(edge.follower, user)))
        if list_name == "following":
            qs = Follow.objects.filter(follower=user).select_related("following").order_by("-created_at")
            return response(True, "Following loaded.", page(request, qs, lambda edge: compact_user(edge.following, user)))
        if list_name == "requests-received":
            qs = FollowRequest.objects.filter(target=user, status=FollowRequest.STATUS_PENDING).select_related("requester").order_by("-created_at")
            return response(True, "Received follow requests loaded.", page(request, qs, follow_request_payload))
        if list_name == "requests-sent":
            qs = FollowRequest.objects.filter(requester=user, status=FollowRequest.STATUS_PENDING).select_related("target").order_by("-created_at")
            return response(True, "Sent follow requests loaded.", page(request, qs, follow_request_payload))
        if list_name == "suggested":
            excluded = {user.phone_number}
            excluded.update(Follow.objects.filter(follower=user).values_list("following_id", flat=True))
            for pair in BlockedUser.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list("blocker_id", "blocked_id"):
                excluded.update(pair)
            qs = get_user_model().objects.filter(is_active=True, is_email_verified=True, privacy_settings__show_in_suggestions=True).exclude(phone_number__in=excluded).order_by("username")
            return response(True, "Suggested users loaded.", page(request, qs, lambda item: compact_user(item, user)))
        return response(False, "Unknown list.", status=404)


@method_decorator(csrf_exempt, name="dispatch")
class RemoveFollowerView(AuthenticatedView):
    def delete(self, request, username):
        follower = get_user_model().objects.get(username__iexact=username)
        removed = remove_follower(request.user_obj, follower)
        return response(True, "Follower removed successfully.", {"removed": removed})


@method_decorator(csrf_exempt, name="dispatch")
class BlockView(AuthenticatedView):
    def get(self, request):
        qs = BlockedUser.objects.filter(blocker=request.user_obj).select_related("blocked").order_by("-created_at")
        return response(True, "Blocked users loaded.", page(request, qs, lambda edge: compact_user(edge.blocked, request.user_obj)))

    def post(self, request, username):
        target = get_user_model().objects.get(username__iexact=username)
        block_user(request.user_obj, target)
        return response(True, "User blocked successfully.")

    def delete(self, request, username):
        target = get_user_model().objects.get(username__iexact=username)
        removed = unblock_user(request.user_obj, target)
        return response(True, "User unblocked successfully.", {"removed": removed})


@method_decorator(csrf_exempt, name="dispatch")
class SimpleRelationshipView(AuthenticatedView):
    model = None
    own_field = "owner"
    target_field = "restricted"
    list_message = "Users loaded."
    add_message = "User added successfully."
    remove_message = "User removed successfully."

    def get(self, request):
        qs = self.model.objects.filter(**{self.own_field: request.user_obj}).order_by("-created_at")
        return response(True, self.list_message, page(request, qs, lambda edge: compact_user(getattr(edge, self.target_field), request.user_obj)))

    def post(self, request, username):
        target = get_user_model().objects.get(username__iexact=username)
        if target == request.user_obj:
            return response(False, "You cannot perform this action on yourself.", status=400)
        if self.model is CloseFriend and users_blocked_between(request.user_obj, target):
            return response(False, "Blocked users cannot be close friends.", status=403)
        defaults = {}
        if self.model is MutedUser:
            payload = body(request)
            defaults = {
                "mute_posts": bool(payload.get("mute_posts", True)),
                "mute_stories": bool(payload.get("mute_stories", False)),
                "mute_messages": bool(payload.get("mute_messages", False)),
            }
        obj, _ = self.model.objects.update_or_create(**{self.own_field: request.user_obj, self.target_field: target}, defaults=defaults)
        return response(True, self.add_message, {"user": compact_user(target, request.user_obj)})

    def delete(self, request, username):
        target = get_user_model().objects.get(username__iexact=username)
        deleted, _ = self.model.objects.filter(**{self.own_field: request.user_obj, self.target_field: target}).delete()
        return response(True, self.remove_message, {"removed": deleted > 0})


class RestrictedView(SimpleRelationshipView):
    model = RestrictedUser
    target_field = "restricted"
    list_message = "Restricted users loaded."
    add_message = "User restricted successfully."
    remove_message = "User unrestricted successfully."


class MutedView(SimpleRelationshipView):
    model = MutedUser
    target_field = "muted"
    list_message = "Muted users loaded."
    add_message = "Mute settings updated successfully."
    remove_message = "User unmuted successfully."


class CloseFriendsView(SimpleRelationshipView):
    model = CloseFriend
    target_field = "friend"
    list_message = "Close friends loaded."
    add_message = "User added to close friends."
    remove_message = "User removed from close friends."

@method_decorator(csrf_exempt, name="dispatch")
class ProfileMediaView(AuthenticatedView):
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    max_size = 5 * 1024 * 1024

    def post(self, request):
        ensure_profile_records(request.user_obj)
        media_type = request.POST.get("type", "profile_picture")
        upload = request.FILES.get("image")
        if media_type not in {"profile_picture", "cover_photo"}:
            return response(False, "Unknown profile media type.", status=400)
        if not upload:
            return response(False, "Image file is required.", status=400)
        if upload.content_type not in self.allowed_types:
            return response(False, "Only JPEG, PNG, and WebP images are allowed.", status=400)
        if upload.size > self.max_size:
            return response(False, "Image must be 5MB or smaller.", status=400)
        if media_type == "profile_picture":
            request.user_obj.profile_picture = upload
            request.user_obj.save(update_fields=["profile_picture", "updated_at"])
        else:
            request.user_obj.profile.cover_photo = upload
            request.user_obj.profile.save(update_fields=["cover_photo", "updated_at"])
        return response(True, "Profile media updated successfully.", {"profile": profile_payload(request.user_obj, request.user_obj, include_private=True)})

    def delete(self, request):
        payload = body(request)
        media_type = payload.get("type", "profile_picture")
        if media_type == "profile_picture":
            request.user_obj.profile_picture.delete(save=False)
            request.user_obj.profile_picture = None
            request.user_obj.save(update_fields=["profile_picture", "updated_at"])
        elif media_type == "cover_photo":
            request.user_obj.profile.cover_photo.delete(save=False)
            request.user_obj.profile.cover_photo = None
            request.user_obj.profile.save(update_fields=["cover_photo", "updated_at"])
        else:
            return response(False, "Unknown profile media type.", status=400)
        return response(True, "Profile media removed successfully.", {"profile": profile_payload(request.user_obj, request.user_obj, include_private=True)})
