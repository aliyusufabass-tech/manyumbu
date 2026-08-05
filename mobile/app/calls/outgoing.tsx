import { useMutation } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect } from "react";
import { Pressable, Text, View } from "react-native";
import { callAction, createCall } from "../../src/api/phase7";
import type { CallType } from "../../src/types/phase7";

export default function OutgoingCallScreen() {
  const params = useLocalSearchParams<{ conversationId?: string; groupId?: string; callType?: CallType }>();
  const create = useMutation({ mutationFn: () => createCall({ call_type: params.callType ?? "private_voice", conversation_id: params.conversationId, group_id: params.groupId }), onSuccess: (result) => router.replace({ pathname: "/calls/[id]", params: { id: result.data.call.id } }) });
  useEffect(() => { if (!create.isPending && !create.data && !create.error) create.mutate(); }, []);
  return <View style={{ flex: 1, backgroundColor: "#0F1F1B", alignItems: "center", justifyContent: "center", padding: 24 }}><Text style={{ color: "white", fontSize: 28, fontWeight: "900" }}>Calling...</Text><Text style={{ color: "#A7F3D0", marginTop: 8 }}>{params.callType?.replace("_", " ") ?? "voice call"}</Text>{create.isError ? <Text style={{ color: "#FCA5A5", marginTop: 18, textAlign: "center" }}>{create.error.message}</Text> : null}<Pressable onPress={() => create.data ? callAction(create.data.data.call.id, "cancel").then(() => router.replace("/calls/ended")) : router.back()} style={{ marginTop: 22, backgroundColor: "#B91C1C", padding: 14, borderRadius: 8 }}><Text style={{ color: "white", fontWeight: "900" }}>Cancel</Text></Pressable></View>;
}
