import type { CompactUser, Paginated } from "./profile";

export type Story = { id: string; author: CompactUser; story_type: "text" | "image" | "video"; caption: string; audience: string | null; background_style: string; link_url: string; location_name: string; replies_enabled: boolean; expires_at: string | null; media: { url: string; media_type: string; file_size: number } | null; view_count: number; viewer_has_viewed: boolean; reaction: string | null; poll: null | { id: number; question: string; total_votes: number; options: Array<{ id: number; text: string; votes: number; percentage: number }> } };
export type Reel = { id: string; author: CompactUser; caption: string; audience: string | null; comments_enabled: boolean; status: string; processing_status: string; video_url: string; thumbnail_url: string; duration: number | null; view_count: number; share_count: number; like_count: number; comment_count: number; viewer_has_liked: boolean; viewer_has_saved: boolean; hashtags: string[] };
export type StoryTray = Paginated<Story>;
export type ReelList = Paginated<Reel>;
