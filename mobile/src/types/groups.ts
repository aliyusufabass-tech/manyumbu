import type { CompactUser, CursorPage, MessageAttachment, MessageStatus, MessageType } from "./messaging";

export type GroupRole = "owner" | "admin" | "moderator" | "member";
export type GroupPrivacy = "private" | "invite_only" | "public";
export type GroupPermission = "everyone" | "moderators" | "admins" | "owner";
export type Group = { id: string; name: string; description: string; image: string | null; owner: CompactUser; privacy: GroupPrivacy; member_count: number; maximum_members: number; status: string; viewer_role: GroupRole | null; viewer_can_send: boolean; muted_until: string | null; archived: boolean; last_message_at: string | null; settings: { who_can_join: string; who_can_send_messages: GroupPermission; who_can_add_members: GroupPermission; who_can_pin_messages: GroupPermission; who_can_mention_everyone: GroupPermission }; created_at: string; updated_at: string };
export type GroupMember = { user: CompactUser; role: GroupRole; joined_at: string };
export type GroupMessage = { id: string; group_id: string; sender: CompactUser; message_type: MessageType; text: string; reply_to?: { id: string; text: string; sender: CompactUser } | null; is_forwarded: boolean; shared_content: Record<string, unknown>; location: Record<string, unknown>; contact: Record<string, unknown>; mentioned_usernames: string[]; status: MessageStatus; is_system: boolean; is_edited: boolean; edited_at: string | null; deleted_for_everyone_at: string | null; removed_by_moderator: boolean; attachments: MessageAttachment[]; reactions: Array<{ username: string; reaction: string }>; viewer_has_starred: boolean; viewer_has_pinned: boolean; read_count: number; delivered_count: number; created_at: string; updated_at: string };
export type GroupInvitation = { id: string; token_preview: string; expires_at: string | null; max_uses: number | null; use_count: number; created_at: string };
export type JoinRequest = { id: string; requester: CompactUser; message: string; created_at: string };
export type AppNotification = { id: string; type: string; message: string; payload: Record<string, unknown>; is_read: boolean; read_at: string | null; seen_at: string | null; created_at: string };
export type NotificationPreferences = Record<string, boolean>;
export type GroupPage = CursorPage<Group>;
export type GroupMessagePage = CursorPage<GroupMessage>;
