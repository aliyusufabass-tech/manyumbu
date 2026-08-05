import { useMutation, useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { callAction, getCall } from "../../src/api/phase7";

export default function IncomingCallScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const callId = String(id);
  const call = useQuery({ queryKey: ["incoming-call", callId], queryFn: () => getCall(callId) });
  const mutation = useMutation({ mutationFn: (action: "accept" | "decline") => callAction(callId, action), onSuccess: (_, action) => router.replace({ pathname: action === "accept" ? "/calls/[id]" : "/calls/ended", params: { id: callId } }) });
  const item = call.data?.data.call;
  return <View style={{ flex: 1, backgroundColor: "#0F1F1B", alignItems: "center", justifyContent: "center", padding: 24 }}><Text style={{ color: "#A7F3D0", fontWeight: "900" }}>{item?.call_type.includes("video") ? "Incoming video call" : "Incoming voice call"}</Text><Text style={{ color: "white", fontSize: 30, fontWeight: "900", marginVertical: 12, textAlign: "center" }}>{item?.group_name || item?.initiator.full_name || "Incoming call"}</Text><View style={{ flexDirection: "row", gap: 18, marginTop: 20 }}><Pressable onPress={() => mutation.mutate("decline")} style={{ backgroundColor: "#B91C1C", padding: 16, borderRadius: 8 }}><Text style={{ color: "white", fontWeight: "900" }}>Decline</Text></Pressable><Pressable onPress={() => mutation.mutate("accept")} style={{ backgroundColor: "#126C57", padding: 16, borderRadius: 8 }}><Text style={{ color: "white", fontWeight: "900" }}>Accept</Text></Pressable></View></View>;
}
