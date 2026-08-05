import { Ionicons } from "@expo/vector-icons";
import { Image, Pressable, ScrollView, Share, Text, View } from "react-native";
import type { Post } from "../types/post";

export function PostCard({ post, onLike, onSave, onOpen }: { post: Post; onLike?: () => void; onSave?: () => void; onOpen?: () => void }) {
  return (
    <Pressable onPress={onOpen} style={{ gap: 12, paddingVertical: 16, borderBottomWidth: 1, borderBottomColor: "#E6EEEA" }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 12 }}>
        <View style={{ flex: 1 }}><Text style={{ fontWeight: "800", color: "#14231F" }}>{post.author.full_name}{post.author.is_verified ? " ?" : ""}</Text><Text style={{ color: "#52605B" }}>@{post.author.username}{post.location_name ? ` · ${post.location_name}` : ""}</Text></View>
        {post.audience ? <Text style={{ color: "#52605B" }}>{post.audience.replace("_", " ")}</Text> : null}
      </View>
      {post.caption ? <Text style={{ color: "#14231F", lineHeight: 22 }}>{post.caption}{post.is_edited ? " · Edited" : ""}</Text> : null}
      {post.media.length ? <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ borderRadius: 8 }}>{post.media.map((item) => item.media_type === "image" ? <Image key={item.id} source={{ uri: item.url }} style={{ width: 280, height: 280, marginRight: 8, borderRadius: 8, backgroundColor: "#DDEBE5" }} /> : <View key={item.id} style={{ width: 280, height: 280, marginRight: 8, borderRadius: 8, backgroundColor: "#14231F", alignItems: "center", justifyContent: "center" }}><Ionicons name="play-circle-outline" size={42} color="white" /><Text style={{ color: "white", marginTop: 8 }}>Video</Text></View>)}</ScrollView> : null}
      {post.hashtags.length ? <Text style={{ color: "#126C57" }}>{post.hashtags.map((tag) => `#${tag}`).join(" ")}</Text> : null}
      <View style={{ flexDirection: "row", gap: 18, alignItems: "center" }}>
        <Pressable onPress={onLike}><Ionicons name={post.viewer_has_liked ? "heart" : "heart-outline"} size={24} color={post.viewer_has_liked ? "#B42318" : "#14231F"} /></Pressable>
        <Ionicons name="chatbubble-outline" size={23} color="#14231F" />
        <Pressable onPress={() => Share.share({ message: `manyumbu://post/${post.id}` })}><Ionicons name="share-social-outline" size={23} color="#14231F" /></Pressable>
        <Pressable onPress={onSave}><Ionicons name={post.viewer_has_saved ? "bookmark" : "bookmark-outline"} size={23} color="#14231F" /></Pressable>
        <Text style={{ color: "#52605B" }}>{post.like_count} likes · {post.comment_count} comments</Text>
      </View>
    </Pressable>
  );
}
