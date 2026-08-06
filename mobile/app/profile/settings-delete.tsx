import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { SafeAreaView, Text, TextInput, View } from "react-native";
import { login, requestAccountDeletion } from "../../src/api/auth";
import { AppHeader } from "../../src/components/AppHeader";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { useAuthStore } from "../../src/store/authStore";
import { colors } from "../../src/theme/theme";

export default function DeleteAccountScreen() {
  const client = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const signOut = useAuthStore((state) => state.signOut);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [reason, setReason] = useState("");
  const mutation = useMutation({ mutationFn: async () => { if (confirm !== "DELETE") throw new Error("Type DELETE to confirm."); await login(user?.username ?? user?.phone_number ?? "", password); return requestAccountDeletion({ reason, recent_auth_confirmed: true }); }, onSuccess: async () => { client.clear(); await signOut(); router.replace("/login"); } });
  return <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}><AppHeader title="Delete account" showBack /><View style={{ padding: 18, gap: 12 }}><Text style={{ color: colors.muted, lineHeight: 22 }}>This requests permanent account deletion and signs you out on this device.</Text><TextInput secureTextEntry placeholder="Password" value={password} onChangeText={setPassword} style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 14 }} /><TextInput placeholder="Reason optional" value={reason} onChangeText={setReason} style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 14 }} /><TextInput autoCapitalize="characters" placeholder="Type DELETE" value={confirm} onChangeText={setConfirm} style={{ borderWidth: 1, borderColor: colors.border, borderRadius: 8, padding: 14 }} />{mutation.error ? <Text style={{ color: colors.error }}>{mutation.error.message}</Text> : null}<PrimaryButton title={mutation.isPending ? "Requesting deletion..." : "Delete account"} variant="danger" onPress={() => mutation.mutate()} disabled={mutation.isPending} /></View></SafeAreaView>;
}
