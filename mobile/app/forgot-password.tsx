import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { forgotPassword } from "../src/api/auth";

export default function ForgotPasswordScreen() {
  const [identifier, setIdentifier] = useState("");
  const mutation = useMutation({ mutationFn: () => forgotPassword(identifier) });
  return (
    <View style={{ flex: 1, padding: 24, paddingTop: 72, backgroundColor: "#FFFFFF", gap: 14 }}>
      <Text style={{ fontSize: 30, fontWeight: "800", color: "#14231F" }}>Reset password</Text>
      <TextInput placeholder="Phone, email, or username" autoCapitalize="none" value={identifier} onChangeText={setIdentifier} style={{ borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 14 }} />
      {mutation.data ? <Text style={{ color: "#126C57" }}>{mutation.data.message}</Text> : null}
      {mutation.error ? <Text style={{ color: "#B42318" }}>{mutation.error.message}</Text> : null}
      <Pressable disabled={mutation.isPending} onPress={() => mutation.mutate()} style={{ backgroundColor: "#126C57", padding: 16, borderRadius: 8, alignItems: "center", opacity: mutation.isPending ? 0.6 : 1 }}>
        <Text style={{ color: "white", fontWeight: "800" }}>{mutation.isPending ? "Sending..." : "Send reset code"}</Text>
      </Pressable>
    </View>
  );
}
