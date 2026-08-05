import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { FlatList, Pressable, Text, View } from "react-native";
import { getUserPosts } from "../api/posts";
import { ScreenState } from "./UserList";

export function PostGrid({ username }: { username: string }) {
  const query = useQuery({ queryKey: ["user-posts", username], queryFn: () => getUserPosts(username), enabled: !!username });
  if (query.isLoading) return <ScreenState text="Loading posts..." />;
  const posts = query.data?.data.results ?? [];
  return <FlatList data={posts} numColumns={3} keyExtractor={(item) => item.id} ListEmptyComponent={<Text style={{ color: "#52605B", paddingVertical: 20 }}>No posts to show yet.</Text>} renderItem={({ item }) => <Pressable onPress={() => router.push({ pathname: "/posts/[id]", params: { id: item.id } })} style={{ flex: 1, aspectRatio: 1, margin: 2, backgroundColor: "#EAF4EF", borderRadius: 8, alignItems: "center", justifyContent: "center", padding: 6 }}><Text numberOfLines={3} style={{ textAlign: "center", color: "#14231F" }}>{item.media.length ? item.post_type : item.caption || "Post"}</Text></Pressable>} />;
}
