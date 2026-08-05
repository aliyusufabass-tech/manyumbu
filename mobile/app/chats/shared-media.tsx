import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { FlatList, Text, View } from "react-native";
import { sharedMedia } from "../../src/api/messaging";

export default function SharedMediaScreen() {
  const { id, kind } = useLocalSearchParams<{ id: string; kind?: string }>();
  const query = useQuery({ queryKey: ["shared-media", id, kind], queryFn: () => sharedMedia(String(id), kind) });
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 54, paddingHorizontal: 18 }}><Text style={{ fontSize: 26, fontWeight: "900", marginBottom: 12 }}>Shared media</Text><FlatList data={query.data?.data.results ?? []} keyExtractor={(item) => `${item.message_id}-${JSON.stringify(item.attachment)}`} ListEmptyComponent={<Text style={{ color: "#6B7280" }}>No shared files yet.</Text>} renderItem={({ item }) => { const attachment = item.attachment as { kind?: string; file_name?: string; file_size?: number }; return <View style={{ paddingVertical: 12, borderBottomWidth: 1, borderColor: "#E5E7EB" }}><Text style={{ fontWeight: "800" }}>{attachment.kind}</Text><Text>{attachment.file_name}</Text><Text style={{ color: "#6B7280" }}>{Math.round((attachment.file_size ?? 0) / 1024)} KB</Text></View>; }} /></View>;
}
