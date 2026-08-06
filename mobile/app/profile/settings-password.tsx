import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, SafeAreaView, Text, TextInput, View } from "react-native";
import { changePassword } from "../../src/api/auth";
import { AppHeader } from "../../src/components/AppHeader";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { useAuthStore } from "../../src/store/authStore";
import { colors } from "../../src/theme/theme";

export default function ChangePasswordScreen() {
  const client = useQueryClient();
  const signOut = useAuthStore((state) => state.signOut);
  const [form, setForm] = useState({ current_password: "", password: "", confirm_password: "" });
  const mutation = useMutation({ mutationFn: () => changePassword(form), onSuccess: async () => { client.clear(); await signOut(); router.replace("/login"); } });
  const update = (key: keyof typeof form, value: string) => setForm((next) => ({ ...next, [key]: value }));
  return <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}><AppHeader title="Change password" showBack /><View style={{ padding: 18, gap: 12 }}><TextInput secureTextEntry placeholder="Current password" value={form.current_password} onChangeText={(v) => update("current_password", v)} style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 14 }} /><TextInput secureTextEntry placeholder="New password" value={form.password} onChangeText={(v) => update("password", v)} style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 14 }} /><TextInput secureTextEntry placeholder="Confirm new password" value={form.confirm_password} onChangeText={(v) => update("confirm_password", v)} style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 14 }} />{mutation.error ? <Text style={{ color: colors.error }}>{mutation.error.message}</Text> : null}<PrimaryButton title={mutation.isPending ? "Saving..." : "Save password"} onPress={() => mutation.mutate()} disabled={mutation.isPending} /></View></SafeAreaView>;
}
