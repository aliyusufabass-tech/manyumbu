import { useMutation, useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { FlatList, Pressable, Text, TextInput, View } from "react-native";
import { listAppeals, listModerationActions, listRestrictions, submitAppeal } from "../../src/api/phase7";
import { validateAppeal } from "../../src/calls/validation";

export default function AppealsScreen() {
  const [selectedAction, setSelectedAction] = useState(""); const [explanation, setExplanation] = useState("");
  const actions = useQuery({ queryKey: ["moderation-actions"], queryFn: listModerationActions });
  const restrictions = useQuery({ queryKey: ["feature-restrictions"], queryFn: listRestrictions });
  const appeals = useQuery({ queryKey: ["appeals"], queryFn: listAppeals });
  const submit = useMutation({ mutationFn: () => { const error = validateAppeal(explanation); if (error) throw new Error(error); return submitAppeal(selectedAction, explanation); }, onSuccess: () => { setExplanation(""); appeals.refetch(); } });
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 48, paddingHorizontal: 18 }}><Pressable onPress={() => router.back()}><Text style={{ color: "#126C57", fontWeight: "900" }}>Back</Text></Pressable><Text style={{ fontSize: 26, fontWeight: "900", marginTop: 16 }}>Moderation</Text><Text style={{ fontWeight: "900", marginTop: 14 }}>Restrictions</Text>{(restrictions.data?.data.results ?? []).map((item) => <Text key={item.id} style={{ color: "#6B7280", paddingVertical: 4 }}>{item.feature}: {item.reason}</Text>)}<Text style={{ fontWeight: "900", marginTop: 14 }}>Appealable actions</Text>{(actions.data?.data.results ?? []).map((item) => <Pressable key={item.id} onPress={() => setSelectedAction(item.id)} style={{ paddingVertical: 8 }}><Text style={{ color: selectedAction === item.id ? "#126C57" : "#111827", fontWeight: "800" }}>{item.action_type}: {item.reason}</Text></Pressable>)}<TextInput value={explanation} onChangeText={setExplanation} placeholder="Appeal explanation" multiline style={{ minHeight: 96, borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 8 }} /><Pressable disabled={!selectedAction} onPress={() => submit.mutate()} style={{ backgroundColor: "#126C57", padding: 14, borderRadius: 8, marginTop: 10, alignItems: "center" }}><Text style={{ color: "white", fontWeight: "900" }}>Submit appeal</Text></Pressable>{submit.isError ? <Text style={{ color: "#B91C1C", marginTop: 8 }}>{submit.error.message}</Text> : null}<FlatList data={appeals.data?.data.results ?? []} keyExtractor={(item) => item.id} renderItem={({ item }) => <View style={{ paddingVertical: 10, borderBottomWidth: 1, borderColor: "#E5E7EB" }}><Text style={{ fontWeight: "800" }}>{item.status}</Text><Text style={{ color: "#6B7280" }}>{item.explanation}</Text></View>} /></View>;
}
