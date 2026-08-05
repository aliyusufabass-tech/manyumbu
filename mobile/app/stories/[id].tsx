import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { getStory, reactStory, replyStory, viewStory, voteStoryPoll } from "../../src/api/phase4";
import { ScreenState } from "../../src/components/UserList";

export default function StoryViewer() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [reply, setReply] = useState("");
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["story", id], queryFn: () => getStory(id ?? ""), enabled: !!id });
  const react = useMutation({ mutationFn: (reaction: string) => reactStory(id ?? "", reaction), onSuccess: () => client.invalidateQueries({ queryKey: ["story", id] }) });
  const sendReply = useMutation({ mutationFn: () => replyStory(id ?? "", reply), onSuccess: () => setReply("") });
  const vote = useMutation({ mutationFn: (option: number) => voteStoryPoll(id ?? "", option), onSuccess: () => client.invalidateQueries({ queryKey: ["story", id] }) });
  useEffect(() => { if (id) viewStory(id); }, [id]);
  if (query.isLoading) return <ScreenState text="Loading story..." />;
  if (!query.data) return <ScreenState text="Story could not be loaded." />;
  const story = query.data.data.story;
  return <View style={{ flex: 1, backgroundColor: story.background_style || "#14231F", padding: 24, paddingTop: 60, justifyContent: "space-between" }}><View style={{ height: 4, backgroundColor: "rgba(255,255,255,.35)", borderRadius: 2 }}><View style={{ width: "55%", height: 4, backgroundColor: "white", borderRadius: 2 }} /></View><View><Text style={{ color: "white", fontWeight: "800", fontSize: 18 }}>@{story.author.username}</Text><Text style={{ color: "white", fontSize: 26, marginTop: 24 }}>{story.caption}</Text>{story.media ? <Text style={{ color: "white", marginTop: 12 }}>{story.media.media_type} story media</Text> : null}{story.poll ? <View style={{ gap: 8, marginTop: 16 }}>{story.poll.options.map((option) => <Pressable key={option.id} onPress={() => vote.mutate(option.id)} style={{ backgroundColor: "rgba(255,255,255,.18)", padding: 12, borderRadius: 8 }}><Text style={{ color: "white" }}>{option.text} · {option.percentage}%</Text></Pressable>)}</View> : null}</View><View style={{ gap: 10 }}><View style={{ flexDirection: "row", gap: 8 }}>{["like", "laugh", "fire", "celebration"].map((r) => <Pressable key={r} onPress={() => react.mutate(r)}><Text style={{ color: "white", fontWeight: "800" }}>{r}</Text></Pressable>)}</View><TextInput placeholder="Reply" placeholderTextColor="#DDEBE5" value={reply} onChangeText={setReply} style={{ borderWidth: 1, borderColor: "rgba(255,255,255,.45)", borderRadius: 8, padding: 12, color: "white" }} /><Pressable onPress={() => sendReply.mutate()}><Text style={{ color: "white", fontWeight: "800" }}>Send reply</Text></Pressable></View></View>;
}
