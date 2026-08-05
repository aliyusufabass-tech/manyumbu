import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { Pressable, Text, TextInput, View } from "react-native";
import { getReel, reelAction } from "../../src/api/phase4";
import { ReelCard } from "../../src/components/ReelCard";
import { ScreenState } from "../../src/components/UserList";
import { useState } from "react";

export default function ReelDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [comment, setComment] = useState("");
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["reel", id], queryFn: () => getReel(id ?? ""), enabled: !!id });
  const action = useMutation({ mutationFn: (kind: string) => reelAction(id ?? "", kind, kind === "comments" ? { text: comment } : {}), onSuccess: () => { setComment(""); client.invalidateQueries({ queryKey: ["reel", id] }); } });
  if (query.isLoading) return <ScreenState text="Loading reel..." />;
  if (!query.data) return <ScreenState text="Reel could not be loaded." />;
  const reel = query.data.data.reel;
  return <View style={{ flex: 1, backgroundColor: "#101816" }}><ReelCard reel={reel} onLike={() => action.mutate("like")} onSave={() => action.mutate("save")} /><View style={{ padding: 16, gap: 8 }}><TextInput placeholder="Comment" value={comment} onChangeText={setComment} style={{ backgroundColor: "white", borderRadius: 8, padding: 12 }} /><Pressable onPress={() => action.mutate("comments")}><Text style={{ color: "white", fontWeight: "800" }}>Post comment</Text></Pressable></View></View>;
}
