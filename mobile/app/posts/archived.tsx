import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { FlatList, Text, View } from "react-native";
import { getArchivedPosts } from "../../src/api/posts";
import { PostCard } from "../../src/components/PostCard";
import { ScreenState } from "../../src/components/UserList";

export default function ArchivedPostsScreen() {
  const query = useQuery({ queryKey: ["archived-posts"], queryFn: () => getArchivedPosts() });
  if (query.isLoading) return <ScreenState text="Loading archive..." />;
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 18, paddingTop: 54 }}><Text style={{ fontSize: 26, fontWeight: "800" }}>Archived posts</Text><FlatList data={query.data?.data.results ?? []} keyExtractor={(item) => item.id} ListEmptyComponent={<ScreenState text="No archived posts." />} renderItem={({ item }) => <PostCard post={item} onOpen={() => router.push({ pathname: "/posts/[id]", params: { id: item.id } })} />} /></View>;
}
