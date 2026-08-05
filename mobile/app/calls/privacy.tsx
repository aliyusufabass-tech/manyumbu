import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { Pressable, Switch, Text, View } from "react-native";
import { getCallPrivacy, updateCallPrivacy } from "../../src/api/phase7";

export default function CallPrivacyScreen() {
  const client = useQueryClient();
  const privacy = useQuery({ queryKey: ["call-privacy"], queryFn: getCallPrivacy });
  const save = useMutation({ mutationFn: (payload: Record<string, unknown>) => updateCallPrivacy(payload), onSuccess: () => client.invalidateQueries({ queryKey: ["call-privacy"] }) });
  const data = privacy.data?.data.privacy ?? {};
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 48, paddingHorizontal: 18 }}><Pressable onPress={() => router.back()}><Text style={{ color: "#126C57", fontWeight: "900" }}>Back</Text></Pressable><Text style={{ fontSize: 28, fontWeight: "900", marginTop: 16 }}>Call privacy</Text>{["allow_voice_calls", "allow_video_calls", "show_call_notifications", "silence_calls_from_unknown_users"].map((key) => <View key={key} style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 14, borderBottomWidth: 1, borderColor: "#E5E7EB" }}><Text>{key.replace(/_/g, " ")}</Text><Switch value={Boolean(data[key])} onValueChange={(value) => save.mutate({ [key]: value })} /></View>)}{["everyone", "people_i_follow", "mutual_followers", "accepted_conversations_only", "no_one"].map((value) => <Pressable key={value} onPress={() => save.mutate({ who_can_call_me: value })} style={{ paddingVertical: 10 }}><Text style={{ color: data.who_can_call_me === value ? "#126C57" : "#111827", fontWeight: "800" }}>{value.replace(/_/g, " ")}</Text></Pressable>)}</View>;
}
