import { useMutation } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, Switch, Text, TextInput, View } from "react-native";
import { createBusinessAccount } from "../../src/api/phase7";
import { validateBusinessForm } from "../../src/calls/validation";

export default function BusinessFormScreen() {
  const [name, setName] = useState(""); const [category, setCategory] = useState(""); const [website, setWebsite] = useState(""); const [showPhone, setShowPhone] = useState(false);
  const mutation = useMutation({ mutationFn: () => { const error = validateBusinessForm(name, category, website); if (error) throw new Error(error); return createBusinessAccount({ business_name: name, business_category: category, website, show_phone_number: showPhone }); }, onSuccess: () => router.replace("/professional") });
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 48, paddingHorizontal: 18 }}><Pressable onPress={() => router.back()}><Text style={{ color: "#126C57", fontWeight: "900" }}>Back</Text></Pressable><Text style={{ fontSize: 26, fontWeight: "900", marginTop: 16 }}>Business account</Text><TextInput value={name} onChangeText={setName} placeholder="Business name" style={{ borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 16 }} /><TextInput value={category} onChangeText={setCategory} placeholder="Business category" style={{ borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 12 }} /><TextInput value={website} onChangeText={setWebsite} placeholder="Website" autoCapitalize="none" style={{ borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 12 }} /><View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 14 }}><Text>Show phone number</Text><Switch value={showPhone} onValueChange={setShowPhone} /></View><Pressable onPress={() => mutation.mutate()} style={{ backgroundColor: "#126C57", padding: 14, borderRadius: 8, marginTop: 16, alignItems: "center" }}><Text style={{ color: "white", fontWeight: "900" }}>Enable business</Text></Pressable>{mutation.isError ? <Text style={{ color: "#B91C1C", marginTop: 10 }}>{mutation.error.message}</Text> : null}</View>;
}
