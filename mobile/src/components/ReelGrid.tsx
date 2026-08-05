import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { FlatList, Pressable, Text } from "react-native";
import { getUserReels } from "../api/phase4";
import { ScreenState } from "./UserList";

export function ReelGrid({ username }: { username: string }) {
  const query = useQuery({ queryKey: ["user-reels", username], queryFn: () => getUserReels(username), enabled: !!username });
  if (query.isLoading) return <ScreenState text="Loading reels..." />;
  const reels = query.data?.data.results ?? [];
  return <FlatList data={reels} numColumns={3} keyExtractor={(item) => item.id} ListEmptyComponent={<Text style={{ color: "#52605B", paddingVertical: 20 }}>No reels to show yet.</Text>} renderItem={({ item }) => <Pressable onPress={() => router.push({ pathname: "/reels/[id]", params: { id: item.id } })} style={{ flex: 1, aspectRatio: 9 / 16, margin: 2, backgroundColor: "#101816", borderRadius: 8, alignItems: "center", justifyContent: "center", padding: 6 }}><Text numberOfLines={3} style={{ textAlign: "center", color: "white" }}>{item.processing_status}</Text></Pressable>} />;
}
