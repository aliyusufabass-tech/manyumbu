import { Ionicons } from "@expo/vector-icons";
import { Image, Pressable, ScrollView, Share, Text, View } from "react-native";
import type { Post } from "../types/post";
import { colors } from "../theme/theme";
import { Avatar } from "./Avatar";

function timeLabel(value: string | null) {
  if (!value) return "now";
  const diff = Math.max(1, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  if (diff < 60) return `${diff}m`;
  if (diff < 1440) return `${Math.floor(diff / 60)}h`;
  return `${Math.floor(diff / 1440)}d`;
}

export function PostCard({ post, onLike, onSave, onOpen }: { post: Post; onLike?: () => void; onSave?: () => void; onOpen?: () => void }) {
  const firstMedia = post.media[0];
  return (
    <Pressable onPress={onOpen} style={({ pressed }) => ({ marginBottom: 16, borderRadius: 18, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.background, overflow: "hidden", opacity: pressed ? 0.96 : 1 })}>
      <View style={{ padding: 14, flexDirection: "row", alignItems: "center", gap: 10 }}>
        <Avatar uri={post.author.profile_picture} name={post.author.full_name || post.author.username} size={42} />
        <View style={{ flex: 1 }}>
          <Text style={{ color: colors.text, fontWeight: "900" }}>{post.author.full_name || post.author.username} {post.author.is_verified ? <Ionicons name="checkmark-circle" size={14} color={colors.primary} /> : null}</Text>
          <Text style={{ color: colors.muted, marginTop: 2 }}>@{post.author.username} · {timeLabel(post.published_at ?? post.created_at)}</Text>
        </View>
        <Ionicons name="ellipsis-horizontal" size={22} color={colors.muted} />
      </View>
      {firstMedia ? (
        <ScrollView horizontal pagingEnabled showsHorizontalScrollIndicator={false}>
          {post.media.map((item) => item.media_type === "image" ? <Image key={item.id} source={{ uri: item.secure_url || item.url }} style={{ width: 342, maxWidth: 342, height: 342, backgroundColor: colors.soft }} resizeMode="cover" /> : <View key={item.id} style={{ width: 342, height: 342, backgroundColor: colors.text, alignItems: "center", justifyContent: "center" }}><Ionicons name="play-circle" size={54} color="white" /><Text style={{ color: "white", marginTop: 8, fontWeight: "700" }}>Video post</Text></View>)}
        </ScrollView>
      ) : <View style={{ paddingHorizontal: 16, paddingBottom: 8 }}><Text style={{ color: colors.text, fontSize: 17, lineHeight: 25 }}>{post.caption}</Text></View>}
      <View style={{ padding: 14, gap: 10 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 18 }}>
          <Pressable onPress={onLike} hitSlop={10}><Ionicons name={post.viewer_has_liked ? "heart" : "heart-outline"} size={26} color={post.viewer_has_liked ? colors.error : colors.text} /></Pressable>
          <Ionicons name="chatbubble-outline" size={24} color={colors.text} />
          <Pressable onPress={() => Share.share({ message: `manyumbu://post/${post.id}` })} hitSlop={10}><Ionicons name="paper-plane-outline" size={24} color={colors.text} /></Pressable>
          <View style={{ flex: 1 }} />
          <Pressable onPress={onSave} hitSlop={10}><Ionicons name={post.viewer_has_saved ? "bookmark" : "bookmark-outline"} size={24} color={colors.text} /></Pressable>
        </View>
        <Text style={{ color: colors.text, fontWeight: "900" }}>{post.like_count} likes</Text>
        {firstMedia && post.caption ? <Text style={{ color: colors.text, lineHeight: 22 }}><Text style={{ fontWeight: "900" }}>{post.author.username}</Text> {post.caption}</Text> : null}
        <Text style={{ color: colors.muted }}>{post.comment_count} comments · {post.share_count} shares</Text>
        {post.hashtags.length ? <Text style={{ color: colors.primary, fontWeight: "700" }}>{post.hashtags.map((tag) => `#${tag}`).join(" ")}</Text> : null}
      </View>
    </Pressable>
  );
}