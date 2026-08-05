import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { FlatList, Pressable, Text, View } from "react-native";
import { getFeed, likePost, savePost, unlikePost, unsavePost } from "../src/api/posts";
import { PostCard } from "../src/components/PostCard";
import { StoryTray } from "../src/components/StoryTray";
import { ScreenState } from "../src/components/UserList";
import type { Post } from "../src/types/post";

export default function FeedScreen() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["feed"], queryFn: () => getFeed() });
  const like = useMutation({ mutationFn: (post: Post) => post.viewer_has_liked ? unlikePost(post.id) : likePost(post.id), onSuccess: () => client.invalidateQueries({ queryKey: ["feed"] }) });
  const save = useMutation({ mutationFn: (post: Post) => post.viewer_has_saved ? unsavePost(post.id) : savePost(post.id), onSuccess: () => client.invalidateQueries({ queryKey: ["feed"] }) });
  if (query.isLoading) return <ScreenState text="Loading feed..." />;
  if (query.isError || !query.data) return <ScreenState text="Feed could not be loaded. Pull to retry." />;
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 48, paddingHorizontal: 18 }}><View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}><Text style={{ fontSize: 26, fontWeight: "800" }}>Home</Text><Pressable onPress={() => router.push("/posts/create")}><Text style={{ color: "#126C57", fontWeight: "800" }}>Create</Text></Pressable></View><FlatList data={query.data.data.results} keyExtractor={(item) => item.id} refreshing={query.isFetching} onRefresh={() => query.refetch()} ListHeaderComponent={<StoryTray />} ListEmptyComponent={<ScreenState text="Follow people or create a post to start your feed." />} renderItem={({ item }) => <PostCard post={item} onOpen={() => router.push({ pathname: "/posts/[id]", params: { id: item.id } })} onLike={() => like.mutate(item)} onSave={() => save.mutate(item)} />} /></View>;
}

