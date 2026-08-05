import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { FlatList, Text, View } from "react-native";
import { getSavedPosts } from "../../src/api/posts";
import { PostCard } from "../../src/components/PostCard";
import { ScreenState } from "../../src/components/UserList";

export default function SavedPostsScreen() {
  const query = useQuery({ queryKey: ["saved-posts"], queryFn: () => getSavedPosts() });
  if (query.isLoading) return <ScreenState text="Loading saved posts..." />;
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 18, paddingTop: 54 }}><Text style={{ fontSize: 26, fontWeight: "800" }}>Saved posts</Text><FlatList data={query.data?.data.results ?? []} keyExtractor={(item) => item.id} ListEmptyComponent={<ScreenState text="No saved posts yet." />} renderItem={({ item }) => <PostCard post={item} onOpen={() => router.push({ pathname: "/posts/[id]", params: { id: item.id } })} />} /></View>;
}
