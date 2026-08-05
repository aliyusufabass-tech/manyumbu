import { useMutation } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { startConversation } from "../../src/api/messaging";

export default function StartChatScreen() {
  const [username, setUsername] = useState("");
  const [initial, setInitial] = useState("");
  const mutation = useMutation({ mutationFn: () => startConversation(username.trim(), initial), onSuccess: (result) => router.replace({ pathname: "/chats/[id]", params: { id: result.data.conversation.id } }) });
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 54, paddingHorizontal: 18 }}><Text style={{ fontSize: 26, fontWeight: "900" }}>New chat</Text><TextInput value={username} onChangeText={setUsername} autoCapitalize="none" placeholder="Username" style={{ borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 18 }} /><TextInput value={initial} onChangeText={setInitial} placeholder="Optional first message" multiline style={{ minHeight: 92, borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 12 }} /><Pressable disabled={!username.trim() || mutation.isPending} onPress={() => mutation.mutate()} style={{ backgroundColor: "#126C57", padding: 14, borderRadius: 8, marginTop: 16, alignItems: "center" }}><Text style={{ color: "white", fontWeight: "900" }}>{mutation.isPending ? "Starting..." : "Start chat"}</Text></Pressable>{mutation.isError ? <Text style={{ color: "#B91C1C", marginTop: 12 }}>{mutation.error.message}</Text> : null}</View>;
}
