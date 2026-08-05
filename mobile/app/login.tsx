import { useMutation } from "@tanstack/react-query";
import { Link, router } from "expo-router";
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { login } from "../src/api/auth";
import { useAuthStore } from "../src/store/authStore";

export default function LoginScreen() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const setSession = useAuthStore((state) => state.setSession);
  const mutation = useMutation({
    mutationFn: () => login(identifier, password),
    async onSuccess(result) {
      await setSession(result.data.user, result.data.tokens);
      router.replace("/(tabs)/home");
    },
  });

  return (
    <View style={{ flex: 1, padding: 24, paddingTop: 72, backgroundColor: "#FFFFFF", gap: 14 }}>
      <Text style={{ fontSize: 30, fontWeight: "800", color: "#14231F" }}>Sign in</Text>
      <TextInput placeholder="Phone, email, or username" autoCapitalize="none" value={identifier} onChangeText={setIdentifier} style={{ borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 14 }} />
      <TextInput placeholder="Password" secureTextEntry value={password} onChangeText={setPassword} style={{ borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 14 }} />
      {mutation.error ? <Text style={{ color: "#B42318" }}>{mutation.error.message}</Text> : null}
      <Pressable disabled={mutation.isPending} onPress={() => mutation.mutate()} style={{ backgroundColor: "#126C57", padding: 16, borderRadius: 8, alignItems: "center", opacity: mutation.isPending ? 0.6 : 1 }}>
        <Text style={{ color: "white", fontWeight: "800" }}>{mutation.isPending ? "Signing in..." : "Sign in"}</Text>
      </Pressable>
      <Link href="/forgot-password"><Text style={{ color: "#126C57", fontWeight: "700" }}>Forgot password?</Text></Link>
    </View>
  );
}
