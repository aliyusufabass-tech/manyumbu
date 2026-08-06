import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { SafeAreaView, Text, TextInput, View } from "react-native";
import { getMyProfile, updateProfile } from "../../src/api/profile";
import { AppHeader } from "../../src/components/AppHeader";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { ScreenState } from "../../src/components/UserList";
import { colors } from "../../src/theme/theme";

export default function ContactInfoScreen() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["profile", "me"], queryFn: getMyProfile });
  const [form, setForm] = useState({ email: "", phone_number: "", date_of_birth: "" });
  useEffect(() => { const p = query.data?.data.profile; if (p) setForm({ email: p.email ?? "", phone_number: p.phone_number ?? "", date_of_birth: p.date_of_birth ?? "" }); }, [query.data]);
  const mutation = useMutation({ mutationFn: () => updateProfile(form), onSuccess: () => client.invalidateQueries({ queryKey: ["profile"] }) });
  if (query.isLoading) return <ScreenState text="Loading contact info..." />;
  return <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}><AppHeader title="Email and phone" showBack /><View style={{ padding: 18, gap: 12 }}><TextInput autoCapitalize="none" keyboardType="email-address" placeholder="Email" value={form.email} onChangeText={(email) => setForm((n) => ({ ...n, email }))} style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 14 }} /><TextInput keyboardType="phone-pad" placeholder="Phone" value={form.phone_number} onChangeText={(phone_number) => setForm((n) => ({ ...n, phone_number }))} style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 14 }} /><TextInput placeholder="Date of birth YYYY-MM-DD" value={form.date_of_birth} onChangeText={(date_of_birth) => setForm((n) => ({ ...n, date_of_birth }))} style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 14 }} />{mutation.error ? <Text style={{ color: colors.error }}>{mutation.error.message}</Text> : null}{mutation.data ? <Text style={{ color: colors.primary }}>{mutation.data.message}</Text> : null}<PrimaryButton title={mutation.isPending ? "Saving..." : "Save contact info"} onPress={() => mutation.mutate()} disabled={mutation.isPending} /></View></SafeAreaView>;
}
