import { useMutation } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { createGroup } from "../../src/api/groups";
import { parseMemberInput, validateGroupDescription, validateGroupName } from "../../src/groups/validation";

export default function CreateGroupScreen() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [members, setMembers] = useState("");
  const [privacy, setPrivacy] = useState<"private" | "invite_only" | "public">("private");
  const mutation = useMutation({ mutationFn: () => { const nameError = validateGroupName(name); const descriptionError = validateGroupDescription(description); if (nameError || descriptionError) throw new Error(nameError ?? descriptionError ?? "Invalid group."); return createGroup({ name: name.trim(), description: description.trim(), privacy, members: parseMemberInput(members) }); }, onSuccess: (result) => router.replace({ pathname: "/groups/[id]", params: { id: result.data.group.id } }) });
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 54, paddingHorizontal: 18 }}><Pressable onPress={() => router.back()}><Text style={{ color: "#126C57", fontWeight: "800" }}>Back</Text></Pressable><Text style={{ fontSize: 26, fontWeight: "900", marginTop: 16 }}>New group</Text><TextInput value={name} onChangeText={setName} placeholder="Group name" style={{ borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 18 }} /><TextInput value={description} onChangeText={setDescription} placeholder="Description" multiline style={{ minHeight: 84, borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 12 }} /><TextInput value={members} onChangeText={setMembers} autoCapitalize="none" placeholder="Members by username, comma separated" style={{ borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 12 }} /><View style={{ flexDirection: "row", gap: 8, marginTop: 12 }}>{(["private", "invite_only", "public"] as const).map((item) => <Pressable key={item} onPress={() => setPrivacy(item)} style={{ padding: 10, borderWidth: 1, borderColor: privacy === item ? "#126C57" : "#D1D5DB", borderRadius: 8 }}><Text style={{ color: privacy === item ? "#126C57" : "#111827", fontWeight: "800" }}>{item.replace("_", " ")}</Text></Pressable>)}</View><Pressable disabled={mutation.isPending} onPress={() => mutation.mutate()} style={{ backgroundColor: "#126C57", padding: 14, borderRadius: 8, marginTop: 16, alignItems: "center" }}><Text style={{ color: "white", fontWeight: "900" }}>{mutation.isPending ? "Creating..." : "Create group"}</Text></Pressable>{mutation.isError ? <Text style={{ color: "#B91C1C", marginTop: 12 }}>{mutation.error.message}</Text> : null}</View>;
}
