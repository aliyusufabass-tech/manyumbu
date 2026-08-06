import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { FlatList, Pressable, SafeAreaView, Text, View } from "react-native";
import { getFeed, likePost, savePost, unlikePost, unsavePost } from "../src/api/posts";
import { AppHeader } from "../src/components/AppHeader";
import { EmptyState } from "../src/components/EmptyState";
import { LoadingSkeleton } from "../src/components/LoadingSkeleton";
import { PostCard } from "../src/components/PostCard";
import { PrimaryButton } from "../src/components/PrimaryButton";
import { StoryTray } from "../src/components/StoryTray";
import { colors } from "../src/theme/theme";
import type { Post } from "../src/types/post";

export default function FeedScreen() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["feed"], queryFn: () => getFeed() });
  const like = useMutation({ mutationFn: (post: Post) => post.viewer_has_liked ? unlikePost(post.id) : likePost(post.id), onSuccess: () => client.invalidateQueries({ queryKey: ["feed"] }) });
  const save = useMutation({ mutationFn: (post: Post) => post.viewer_has_saved ? unsavePost(post.id) : savePost(post.id), onSuccess: () => client.invalidateQueries({ queryKey: ["feed"] }) });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.soft }}>
      <AppHeader title="Manyumbu" actions={[{ icon: "notifications-outline", label: "Notifications", onPress: () => router.push("/notifications") }, { icon: "chatbubble-ellipses-outline", label: "Chats", onPress: () => router.push("/chats") }]} />
      {query.isLoading ? <LoadingSkeleton rows={3} /> : null}
      {query.isError ? <EmptyState icon="cloud-offline-outline" title="Feed could not be loaded" message="Check your connection and pull to retry." actionLabel="Retry" onAction={() => query.refetch()} /> : null}
      {!query.isLoading && !query.isError ? (
        <FlatList
          data={query.data?.data.results ?? []}
          keyExtractor={(item) => item.id}
          refreshing={query.isFetching}
          onRefresh={() => query.refetch()}
          contentContainerStyle={{ padding: 14, paddingBottom: 96 }}
          ListHeaderComponent={<StoryTray />}
          ListEmptyComponent={<View style={{ marginTop: 36 }}><EmptyState icon="images-outline" title="Your feed is quiet" message="Follow people or create your first post to bring your timeline to life." /><View style={{ flexDirection: "row", gap: 10, paddingHorizontal: 18 }}><View style={{ flex: 1 }}><PrimaryButton title="Find people" variant="secondary" onPress={() => router.push("/(tabs)/explore")} /></View><View style={{ flex: 1 }}><PrimaryButton title="Create post" onPress={() => router.push("/posts/create")} /></View></View></View>}
          renderItem={({ item }) => <PostCard post={item} onOpen={() => router.push({ pathname: "/posts/[id]", params: { id: item.id } })} onLike={() => like.mutate(item)} onSave={() => save.mutate(item)} />}
        />
      ) : null}
      <Pressable onPress={() => router.push("/posts/create")} style={{ position: "absolute", right: 18, bottom: 82, backgroundColor: colors.primary, borderRadius: 999, paddingHorizontal: 18, height: 48, alignItems: "center", justifyContent: "center" }}><Text style={{ color: "white", fontWeight: "900" }}>Create</Text></Pressable>
    </SafeAreaView>
  );
}