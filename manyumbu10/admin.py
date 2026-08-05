from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AdminAuditLog, BlockedUser, CloseFriend, Comment, CommentLike, EmailVerificationCode, Follow, FollowRequest, GoogleAccount, Hashtag, HiddenPost, HiddenReel, MutedUser, Notification, PasswordResetCode, Post, PostAudienceUser, PostHashtag, PostLike, PostMedia, PostMention, PostReport, PostTag, Reel, ReelAudienceUser, ReelComment, ReelHashtag, ReelLike, ReelMention, ReelNotInterested, ReelReport, ReelTag, ReelView, RestrictedUser, SavedPost, SavedReel, Story, StoryAudienceUser, StoryHashtag, StoryHiddenUser, StoryHighlight, StoryHighlightItem, StoryMedia, StoryMention, StoryPoll, StoryPollOption, StoryPollVote, StoryReaction, StoryReply, StoryReport, StoryView, User, UserPrivacySettings, UserProfile, UserSession


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ("phone_number",)
    list_display = ("phone_number", "username", "email", "is_email_verified", "is_active", "is_staff")
    search_fields = ("phone_number", "username", "email", "full_name")
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal info", {"fields": ("email", "username", "full_name", "date_of_birth", "profile_picture")}),
        ("Verification", {"fields": ("is_email_verified", "email_verified_at", "is_verified")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Roles", {"fields": ("is_creator", "is_business")}),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone_number", "email", "username", "full_name", "date_of_birth", "password1", "password2", "is_active", "is_email_verified"),
        }),
    )
    readonly_fields = ("created_at", "updated_at")


admin.site.register(UserProfile)
admin.site.register(UserSession)
admin.site.register(EmailVerificationCode)
admin.site.register(PasswordResetCode)
admin.site.register(GoogleAccount)

admin.site.register(UserPrivacySettings)
admin.site.register(Follow)
admin.site.register(FollowRequest)
admin.site.register(BlockedUser)
admin.site.register(RestrictedUser)
admin.site.register(MutedUser)
admin.site.register(CloseFriend)


admin.site.register(Post)
admin.site.register(PostMedia)
admin.site.register(PostLike)
admin.site.register(SavedPost)
admin.site.register(HiddenPost)
admin.site.register(PostTag)
admin.site.register(PostMention)
admin.site.register(PostAudienceUser)
admin.site.register(Hashtag)
admin.site.register(PostHashtag)
admin.site.register(Comment)
admin.site.register(CommentLike)
admin.site.register(Notification)
admin.site.register(PostReport)
admin.site.register(AdminAuditLog)


admin.site.register(Story)
admin.site.register(StoryMedia)
admin.site.register(StoryView)
admin.site.register(StoryReaction)
admin.site.register(StoryReply)
admin.site.register(StoryMention)
admin.site.register(StoryHashtag)
admin.site.register(StoryAudienceUser)
admin.site.register(StoryHiddenUser)
admin.site.register(StoryPoll)
admin.site.register(StoryPollOption)
admin.site.register(StoryPollVote)
admin.site.register(StoryHighlight)
admin.site.register(StoryHighlightItem)
admin.site.register(StoryReport)
admin.site.register(Reel)
admin.site.register(ReelLike)
admin.site.register(SavedReel)
admin.site.register(ReelView)
admin.site.register(HiddenReel)
admin.site.register(ReelNotInterested)
admin.site.register(ReelTag)
admin.site.register(ReelMention)
admin.site.register(ReelHashtag)
admin.site.register(ReelAudienceUser)
admin.site.register(ReelComment)
admin.site.register(ReelReport)


from .models import Conversation, ConversationArchive, ConversationClearState, ConversationMute, ConversationParticipant, ConversationReport, Message, MessageAttachment, MessageDeletion, MessageDeliveryReceipt, MessagePin, MessageReaction, MessageReadReceipt, MessageReport, MessageRequest, MessageStar, UserDevice, UserPresence, WebSocketSession

for model in [Conversation, ConversationParticipant, Message, MessageAttachment, MessageDeletion, MessageReaction, MessageReadReceipt, MessageDeliveryReceipt, MessageStar, MessagePin, ConversationMute, ConversationArchive, ConversationClearState, MessageRequest, MessageReport, ConversationReport, UserPresence, UserDevice, WebSocketSession]:
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass

from .models import AdminAnnouncement, Group, GroupArchive, GroupAuditLog, GroupBan, GroupClearState, GroupInvitation, GroupJoinRequest, GroupMember, GroupMessage, GroupMessageAttachment, GroupMessageDeletion, GroupMessageDeliveryReceipt, GroupMessagePin, GroupMessageReaction, GroupMessageReadReceipt, GroupMessageReport, GroupMessageStar, GroupMute, GroupReport, GroupRestriction, GroupRole, GroupSettings, NotificationBatch, NotificationDelivery, NotificationPreference, PushNotificationDelivery

for model in [Group, GroupRole, GroupSettings, GroupMember, GroupInvitation, GroupJoinRequest, GroupBan, GroupRestriction, GroupMessage, GroupMessageAttachment, GroupMessageReaction, GroupMessageReadReceipt, GroupMessageDeliveryReceipt, GroupMessageDeletion, GroupMessageStar, GroupMessagePin, GroupMute, GroupArchive, GroupClearState, GroupReport, GroupMessageReport, GroupAuditLog, NotificationPreference, NotificationDelivery, PushNotificationDelivery, NotificationBatch, AdminAnnouncement]:
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass
