import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { FlatList, Pressable, Text, TextInput, View } from "react-native";
import { groupAction, listGroups } from "../../src/api/groups";
import type { Group } from "../../src/types/groups";

function GroupRow({ item, onArchive }: { item: Group; onArchive: () => void }) {
  return <Pressable onPress={() => router.push({ pathname: "/groups/[id]", params: { id: item.id } })} style={{ paddingVertical: 14, borderBottomWidth: 1, borderColor: "#E5E7EB", flexDirection: "row", gap: 12 }}><View style={{ width: 48, height: 48, borderRadius: 24, backgroundColor: "#126C57", alignItems: "center", justifyContent: "center" }}><Text style={{ color: "white", fontWeight: "900" }}>{item.name[0]?.toUpperCase() ?? "G"}</Text></View><View style={{ flex: 1 }}><View style={{ flexDirection: "row", justifyContent: "space-between" }}><Text style={{ fontSize: 16, fontWeight: "900" }}>{item.name}</Text><Text style={{ color: "#6B7280", fontSize: 12 }}>{item.last_message_at ? new Date(item.last_message_at).toLocaleTimeString() : ""}</Text></View><Text numberOfLines={1} style={{ color: "#4B5563", marginTop: 3 }}>{item.description || `${item.member_count} members`}</Text><View style={{ flexDirection: "row", gap: 10, marginTop: 8 }}><Text style={{ color: "#6B7280" }}>{item.viewer_role ?? item.privacy}</Text><Pressable onPress={onArchive}><Text style={{ color: "#126C57", fontWeight: "800" }}>{item.archived ? "Unarchive" : "Archive"}</Text></Pressable>{item.muted_until ? <Text style={{ color: "#9CA3AF" }}>Muted</Text> : null}</View></View></Pressable>;
}

export default function GroupsScreen() {
  const [q, setQ] = useState("");
  const [archived, setArchived] = useState(false);
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["groups", q, archived], queryFn: () => listGroups({ q, archived }) });
  const action = useMutation({ mutationFn: ({ id, name }: { id: string; name: "archive" | "unarchive" }) => groupAction(id, name), onSuccess: () => client.invalidateQueries({ queryKey: ["groups"] }) });
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 48, paddingHorizontal: 18 }}><View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}><Text style={{ fontSize: 28, fontWeight: "900" }}>Groups</Text><Pressable onPress={() => router.push("/groups/create")}><Text style={{ color: "#126C57", fontWeight: "900" }}>New</Text></Pressable></View><View style={{ flexDirection: "row", gap: 10, marginVertical: 12 }}><TextInput value={q} onChangeText={setQ} placeholder="Search groups" style={{ flex: 1, borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12 }} /><Pressable onPress={() => setArchived(!archived)} style={{ justifyContent: "center" }}><Text style={{ color: "#126C57", fontWeight: "800" }}>{archived ? "Active" : "Archived"}</Text></Pressable></View><Pressable onPress={() => router.push("/notifications")}><Text style={{ color: "#126C57", fontWeight: "800", marginBottom: 8 }}>Notifications</Text></Pressable>{query.isLoading ? <Text>Loading groups...</Text> : null}{query.isError ? <Text>Groups could not be loaded.</Text> : null}<FlatList data={query.data?.data.results ?? []} keyExtractor={(item) => item.id} refreshing={query.isFetching} onRefresh={() => query.refetch()} ListEmptyComponent={<Text style={{ color: "#6B7280", marginTop: 24 }}>No groups yet.</Text>} renderItem={({ item }) => <GroupRow item={item} onArchive={() => action.mutate({ id: item.id, name: item.archived ? "unarchive" : "archive" })} />} /></View>;
}
