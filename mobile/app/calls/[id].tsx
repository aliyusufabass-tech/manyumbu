import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { callAction, getCall, reportCall } from "../../src/api/phase7";
import { openCallSocket, sendCallSocketEvent } from "../../src/calls/socket";
import { callIsTerminal, nativeWebRtcStatus } from "../../src/calls/validation";
import type { CallEvent } from "../../src/types/phase7";

export default function CallDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const callId = String(id);
  const client = useQueryClient();
  const [connection, setConnection] = useState("connecting");
  const [muted, setMuted] = useState(false);
  const [camera, setCamera] = useState(false);
  const [speaker, setSpeaker] = useState(true);
  const [quality, setQuality] = useState("unknown");
  const [reportReason, setReportReason] = useState("harassment");
  const socket = useRef<WebSocket | null>(null);
  const call = useQuery({ queryKey: ["call", callId], queryFn: () => getCall(callId), refetchInterval: 5000 });
  useEffect(() => { let active = true; openCallSocket(callId, (event: CallEvent) => { if (event.event === "connection.ready") setConnection("connected"); if (event.event === "call.state_updated") setQuality(String(event.data.state ?? "connected")); if (["call.accepted", "call.declined", "call.cancelled", "call.ended", "call.participant_joined", "call.participant_left"].includes(event.event)) client.invalidateQueries({ queryKey: ["call", callId] }); }).then((ws) => { if (!active) { ws.close(); return; } socket.current = ws; ws.onopen = () => setConnection("connected"); ws.onclose = () => setConnection("offline"); ws.onerror = () => setConnection("offline"); }); return () => { active = false; socket.current?.close(); }; }, [callId, client]);
  const lifecycle = useMutation({ mutationFn: (action: "accept" | "decline" | "cancel" | "end" | "join" | "leave") => callAction(callId, action, { for_all: action === "end", camera_enabled: camera }), onSuccess: () => { client.invalidateQueries({ queryKey: ["call", callId] }); client.invalidateQueries({ queryKey: ["calls"] }); } });
  const report = useMutation({ mutationFn: () => reportCall(callId, reportReason, "Reported from mobile call screen") });
  const item = call.data?.data.call;
  const nativeStatus = nativeWebRtcStatus(item?.signaling);
  const terminal = item ? callIsTerminal(item.status) : false;
  return <View style={{ flex: 1, backgroundColor: "#0F1F1B", paddingTop: 48, paddingHorizontal: 18 }}><Pressable onPress={() => router.back()}><Text style={{ color: "#A7F3D0", fontWeight: "900" }}>Back</Text></Pressable><View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 12 }}><Text style={{ color: "white", fontSize: 28, fontWeight: "900", textAlign: "center" }}>{item?.group_name || item?.peer?.full_name || "Call"}</Text><Text style={{ color: "#D1FAE5" }}>{item?.call_type.replace("_", " ")} · {item?.status} · {connection}</Text><Text style={{ color: "#A7F3D0", textAlign: "center" }}>{nativeStatus === "development_build_required" ? "Native WebRTC requires a custom Expo development build." : nativeStatus === "signaling_only_without_turn" ? "Signaling is available; configure TURN for reliable production calls." : "Media capability available."}</Text><Text style={{ color: "#D1FAE5" }}>Quality: {quality} · Speaker {speaker ? "on" : "off"}</Text><View style={{ flexDirection: "row", flexWrap: "wrap", justifyContent: "center", gap: 10 }}><Pressable disabled={terminal} onPress={() => lifecycle.mutate("accept")} style={{ backgroundColor: "#126C57", padding: 12, borderRadius: 8 }}><Text style={{ color: "white", fontWeight: "900" }}>Accept</Text></Pressable><Pressable disabled={terminal} onPress={() => lifecycle.mutate("decline")} style={{ backgroundColor: "#B91C1C", padding: 12, borderRadius: 8 }}><Text style={{ color: "white", fontWeight: "900" }}>Decline</Text></Pressable><Pressable disabled={terminal} onPress={() => lifecycle.mutate("end")} style={{ backgroundColor: "#374151", padding: 12, borderRadius: 8 }}><Text style={{ color: "white", fontWeight: "900" }}>End</Text></Pressable><Pressable onPress={() => { setMuted(!muted); sendCallSocketEvent(socket.current, "call.mute_updated", { is_muted: !muted }); }} style={{ backgroundColor: "#1F2937", padding: 12, borderRadius: 8 }}><Text style={{ color: "white" }}>{muted ? "Unmute" : "Mute"}</Text></Pressable><Pressable onPress={() => { setCamera(!camera); sendCallSocketEvent(socket.current, "call.camera_updated", { camera_enabled: !camera }); }} style={{ backgroundColor: "#1F2937", padding: 12, borderRadius: 8 }}><Text style={{ color: "white" }}>{camera ? "Camera off" : "Camera on"}</Text></Pressable><Pressable onPress={() => setSpeaker(!speaker)} style={{ backgroundColor: "#1F2937", padding: 12, borderRadius: 8 }}><Text style={{ color: "white" }}>Speaker</Text></Pressable></View><View style={{ width: "100%", marginTop: 20 }}><TextInput value={reportReason} onChangeText={setReportReason} style={{ backgroundColor: "white", borderRadius: 8, padding: 12 }} /><Pressable onPress={() => report.mutate()} style={{ marginTop: 8 }}><Text style={{ color: "#A7F3D0", fontWeight: "900" }}>Report call</Text></Pressable></View></View></View>;
}
