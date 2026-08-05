import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { FlatList, Pressable, Text, View } from "react-native";
import { listCalls } from "../../src/api/phase7";
import type { Call } from "../../src/types/phase7";

function rowTitle(call: Call) { return call.group_name || call.peer?.full_name || call.initiator.full_name; }
export default function CallHistoryScreen() {
  const calls = useQuery({ queryKey: ["calls"], queryFn: () => listCalls() });
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 48, paddingHorizontal: 18 }}><View style={{ flexDirection: "row", justifyContent: "space-between" }}><Text style={{ fontSize: 28, fontWeight: "900" }}>Calls</Text><Pressable onPress={() => router.push("/calls/privacy")}><Text style={{ color: "#126C57", fontWeight: "900" }}>Privacy</Text></Pressable></View>{calls.isLoading ? <Text>Loading calls...</Text> : null}{calls.isError ? <Text>Call history could not be loaded.</Text> : null}<FlatList data={calls.data?.data.results ?? []} keyExtractor={(item) => item.id} ListEmptyComponent={<Text style={{ color: "#6B7280", marginTop: 24 }}>No call history yet.</Text>} renderItem={({ item }) => <Pressable onPress={() => router.push({ pathname: "/calls/[id]", params: { id: item.id } })} style={{ paddingVertical: 14, borderBottomWidth: 1, borderColor: "#E5E7EB" }}><Text style={{ fontWeight: "900", fontSize: 16 }}>{rowTitle(item)}</Text><Text style={{ color: "#4B5563", marginTop: 4 }}>{item.call_type.replace("_", " ")} · {item.status} · {item.duration_seconds}s</Text><Text style={{ color: "#6B7280", marginTop: 2 }}>{new Date(item.created_at).toLocaleString()}</Text></Pressable>} /></View>;
}
