import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { FlatList, Pressable, Text, TextInput, View } from "react-native";
import { addComment, getComments, getPost, likePost, savePost, unlikePost, unsavePost } from "../../src/api/posts";
import { PostCard } from "../../src/components/PostCard";
import { ScreenState } from "../../src/components/UserList";

export default function PostDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [text, setText] = useState("");
  const client = useQueryClient();
  const post = useQuery({ queryKey: ["post", id], queryFn: () => getPost(id ?? ""), enabled: !!id });
  const comments = useQuery({ queryKey: ["comments", id], queryFn: () => getComments(id ?? ""), enabled: !!id });
  const like = useMutation({ mutationFn: () => post.data?.data.post.viewer_has_liked ? unlikePost(id ?? "") : likePost(id ?? ""), onSuccess: () => client.invalidateQueries({ queryKey: ["post", id] }) });
  const save = useMutation({ mutationFn: () => post.data?.data.post.viewer_has_saved ? unsavePost(id ?? "") : savePost(id ?? ""), onSuccess: () => client.invalidateQueries({ queryKey: ["post", id] }) });
  const comment = useMutation({ mutationFn: () => addComment(id ?? "", text), onSuccess: () => { setText(""); client.invalidateQueries({ queryKey: ["comments", id] }); client.invalidateQueries({ queryKey: ["post", id] }); } });
  if (post.isLoading) return <ScreenState text="Loading post..." />;
  if (!post.data) return <ScreenState text="Post could not be loaded." />;
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 18, paddingTop: 54 }}><FlatList ListHeaderComponent={<><PostCard post={post.data.data.post} onLike={() => like.mutate()} onSave={() => save.mutate()} /><View style={{ flexDirection: "row", gap: 8, paddingVertical: 12 }}><TextInput placeholder="Add a comment" value={text} onChangeText={setText} style={{ flex: 1, borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 12 }} /><Pressable onPress={() => comment.mutate()} style={{ backgroundColor: "#126C57", padding: 12, borderRadius: 8 }}><Text style={{ color: "white", fontWeight: "800" }}>Post</Text></Pressable></View></>} data={comments.data?.data.results ?? []} keyExtractor={(item) => item.id} renderItem={({ item }) => <View style={{ paddingVertical: 10 }}><Text style={{ fontWeight: "800" }}>{item.author.username}</Text><Text>{item.text || "Deleted comment"}{item.is_edited ? " · Edited" : ""}</Text></View>} /></View>;
}
