export function validateStoryDraft(input: { text: string; media?: { type: string; size?: number }; pollOptions?: string[]; linkUrl?: string }) {
  const errors: string[] = [];
  if (!input.text.trim() && !input.media) errors.push("Story needs text or media.");
  if (input.text.length > 1000) errors.push("Story text must be 1000 characters or fewer.");
  if (input.media?.type.startsWith("image/") && (input.media.size ?? 0) > 8 * 1024 * 1024) errors.push("Story image must be 8MB or smaller.");
  if (input.media?.type.startsWith("video/") && (input.media.size ?? 0) > 60 * 1024 * 1024) errors.push("Story video must be 60MB or smaller.");
  if (input.pollOptions && (input.pollOptions.filter(Boolean).length < 2 || input.pollOptions.filter(Boolean).length > 4)) errors.push("Polls need two to four options.");
  if (input.linkUrl && !/^https?:\/\//.test(input.linkUrl)) errors.push("Links must start with http or https.");
  return errors;
}

export function validateReelDraft(input: { caption: string; video?: { type: string; size?: number; duration?: number } }) {
  const errors: string[] = [];
  if (!input.video) errors.push("Reel video is required.");
  if (input.caption.length > 2200) errors.push("Caption must be 2200 characters or fewer.");
  if (input.video && !input.video.type.startsWith("video/")) errors.push("Choose a supported video file.");
  if ((input.video?.size ?? 0) > 120 * 1024 * 1024) errors.push("Reel video must be 120MB or smaller.");
  if ((input.video?.duration ?? 1) <= 0) errors.push("Reel duration must be valid.");
  return errors;
}
