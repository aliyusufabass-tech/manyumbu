export type ComposerDraft = { caption: string; media: Array<{ type: string; size?: number }>; audience: string; commentsEnabled: boolean };

export function validateComposerDraft(draft: ComposerDraft) {
  const errors: string[] = [];
  const hasText = draft.caption.trim().length > 0;
  if (!hasText && draft.media.length === 0) errors.push("Post must include text or media.");
  if (draft.caption.length > 2200) errors.push("Caption must be 2200 characters or fewer.");
  const images = draft.media.filter((item) => item.type.startsWith("image/"));
  const videos = draft.media.filter((item) => item.type.startsWith("video/"));
  if (images.length > 10) errors.push("Choose at most 10 images.");
  if (videos.length > 1 || (videos.length && images.length)) errors.push("Choose one video or up to 10 images, not mixed media.");
  if (images.some((item) => (item.size ?? 0) > 8 * 1024 * 1024)) errors.push("Each image must be 8MB or smaller.");
  if (videos.some((item) => (item.size ?? 0) > 80 * 1024 * 1024)) errors.push("Video must be 80MB or smaller.");
  return errors;
}
