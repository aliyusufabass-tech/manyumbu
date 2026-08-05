import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { FlatList, Pressable, Text, View } from "react-native";
import { getReelFeed, reelAction } from "../../src/api/phase4";
import { ReelCard } from "../../src/components/ReelCard";
import { ScreenState } from "../../src/components/UserList";
import type { Reel } from "../../src/types/phase4";

export default function ReelFeedScreen() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["reels", "feed"], queryFn: () => getReelFeed() });
  const action = useMutation({ mutationFn: ({ reel, kind }: { reel: Reel; kind: string }) => reelAction(reel.id, kind), onSuccess: () => client.invalidateQueries({ queryKey: ["reels"] }) });
  if (query.isLoading) return <ScreenState text="Loading reels..." />;
  return <View style={{ flex: 1, backgroundColor: "#101816" }}><Pressable onPress={() => router.push("/reels/create")} style={{ position: "absolute", right: 18, top: 54, zIndex: 2 }}><Text style={{ color: "white", fontWeight: "800" }}>Create</Text></Pressable><FlatList pagingEnabled data={query.data?.data.results ?? []} keyExtractor={(item) => item.id} ListEmptyComponent={<ScreenState text="No reels yet." />} renderItem={({ item }) => <ReelCard reel={item} onLike={() => action.mutate({ reel: item, kind: "like" })} onSave={() => action.mutate({ reel: item, kind: "save" })} />} /></View>;
}
