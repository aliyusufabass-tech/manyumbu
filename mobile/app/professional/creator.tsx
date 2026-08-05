import { useMutation } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { createCreatorAccount } from "../../src/api/phase7";
import { validateCreatorForm } from "../../src/calls/validation";

export default function CreatorFormScreen() {
  const [category, setCategory] = useState(""); const [bio, setBio] = useState(""); const [email, setEmail] = useState("");
  const mutation = useMutation({ mutationFn: () => { const error = validateCreatorForm(category, bio); if (error) throw new Error(error); return createCreatorAccount({ creator_category: category, professional_bio: bio, collaboration_email: email }); }, onSuccess: () => router.replace("/professional") });
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 48, paddingHorizontal: 18 }}><Pressable onPress={() => router.back()}><Text style={{ color: "#126C57", fontWeight: "900" }}>Back</Text></Pressable><Text style={{ fontSize: 26, fontWeight: "900", marginTop: 16 }}>Creator account</Text><TextInput value={category} onChangeText={setCategory} placeholder="Creator category" style={{ borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 16 }} /><TextInput value={bio} onChangeText={setBio} placeholder="Professional bio" multiline style={{ minHeight: 92, borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 12 }} /><TextInput value={email} onChangeText={setEmail} placeholder="Collaboration email" autoCapitalize="none" style={{ borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 12 }} /><Pressable onPress={() => mutation.mutate()} style={{ backgroundColor: "#126C57", padding: 14, borderRadius: 8, marginTop: 16, alignItems: "center" }}><Text style={{ color: "white", fontWeight: "900" }}>Enable creator</Text></Pressable>{mutation.isError ? <Text style={{ color: "#B91C1C", marginTop: 10 }}>{mutation.error.message}</Text> : null}</View>;
}
