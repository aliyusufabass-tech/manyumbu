import { useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { FlatList, Text, View } from "react-native";
import { getHashtagPosts } from "../../src/api/posts";
import { PostCard } from "../../src/components/PostCard";
import { ScreenState } from "../../src/components/UserList";

export default function HashtagScreen() {
  const { tag } = useLocalSearchParams<{ tag: string }>();
  const query = useQuery({ queryKey: ["hashtag", tag], queryFn: () => getHashtagPosts(tag ?? ""), enabled: !!tag });
  if (query.isLoading) return <ScreenState text="Loading hashtag..." />;
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 18, paddingTop: 54 }}><Text style={{ fontSize: 26, fontWeight: "800" }}>#{tag}</Text><FlatList data={query.data?.data.results ?? []} keyExtractor={(item) => item.id} ListEmptyComponent={<ScreenState text="No visible posts for this hashtag." />} renderItem={({ item }) => <PostCard post={item} onOpen={() => router.push({ pathname: "/posts/[id]", params: { id: item.id } })} />} /></View>;
}
