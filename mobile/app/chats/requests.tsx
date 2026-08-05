import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FlatList, Pressable, Text, View } from "react-native";
import { listMessageRequests, messageRequestAction, deleteMessageRequest } from "../../src/api/messaging";

export default function MessageRequestsScreen() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["message-requests"], queryFn: listMessageRequests });
  const action = useMutation({ mutationFn: async ({ id, name }: { id: string; name: "accept" | "reject" | "spam" | "delete" }): Promise<unknown> => name === "delete" ? deleteMessageRequest(id) : messageRequestAction(id, name), onSuccess: () => client.invalidateQueries({ queryKey: ["message-requests"] }) });
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 54, paddingHorizontal: 18 }}><Text style={{ fontSize: 26, fontWeight: "900", marginBottom: 12 }}>Requests</Text><FlatList data={query.data?.data.results ?? []} keyExtractor={(item) => item.id} ListEmptyComponent={<Text style={{ color: "#6B7280" }}>No pending requests.</Text>} renderItem={({ item }) => <View style={{ borderBottomWidth: 1, borderColor: "#E5E7EB", paddingVertical: 14 }}><Text style={{ fontWeight: "900" }}>{item.sender.full_name}</Text><Text style={{ color: "#4B5563", marginVertical: 6 }}>{item.preview_text || "Message request"}</Text><View style={{ flexDirection: "row", gap: 12 }}><Pressable onPress={() => action.mutate({ id: item.id, name: "accept" })}><Text style={{ color: "#126C57", fontWeight: "800" }}>Accept</Text></Pressable><Pressable onPress={() => action.mutate({ id: item.id, name: "reject" })}><Text>Reject</Text></Pressable><Pressable onPress={() => action.mutate({ id: item.id, name: "spam" })}><Text style={{ color: "#B91C1C" }}>Spam</Text></Pressable><Pressable onPress={() => action.mutate({ id: item.id, name: "delete" })}><Text>Delete</Text></Pressable></View></View>} /></View>;
}

