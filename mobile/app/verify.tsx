import { useMutation } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useRef, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { resendCode, verifyEmail } from "../src/api/auth";
import { useAuthStore } from "../src/store/authStore";

export default function VerifyScreen() {
  const { phone } = useLocalSearchParams<{ phone: string }>();
  const [digits, setDigits] = useState(["", "", "", "", "", ""]);
  const inputs = useRef<Array<TextInput | null>>([]);
  const setSession = useAuthStore((state) => state.setSession);
  const verify = useMutation({
    mutationFn: () => verifyEmail(phone ?? "", digits.join("")),
    async onSuccess(result) {
      await setSession(result.data.user, result.data.tokens);
      router.replace("/(tabs)/home");
    },
  });
  const resend = useMutation({ mutationFn: () => resendCode(phone ?? "") });

  function setDigit(index: number, value: string) {
    const chars = value.replace(/\D/g, "").slice(0, 6).split("");
    const next = [...digits];
    if (chars.length > 1) {
      chars.forEach((char, offset) => { if (index + offset < 6) next[index + offset] = char; });
      setDigits(next);
      inputs.current[Math.min(index + chars.length, 5)]?.focus();
      return;
    }
    next[index] = chars[0] ?? "";
    setDigits(next);
    if (chars[0] && index < 5) inputs.current[index + 1]?.focus();
  }

  return (
    <View style={{ flex: 1, padding: 24, paddingTop: 72, backgroundColor: "#FFFFFF", gap: 18 }}>
      <Text style={{ fontSize: 30, fontWeight: "800", color: "#14231F" }}>Verify email</Text>
      <Text style={{ color: "#52605B", lineHeight: 22 }}>Enter the six-digit code sent to your email.</Text>
      <View style={{ flexDirection: "row", gap: 8 }}>
        {digits.map((digit, index) => (
          <TextInput key={index} ref={(node) => { inputs.current[index] = node; }} keyboardType="number-pad" maxLength={6} value={digit} onChangeText={(value) => setDigit(index, value)} style={{ flex: 1, borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 12, textAlign: "center", fontSize: 20, fontWeight: "800" }} />
        ))}
      </View>
      {verify.error ? <Text style={{ color: "#B42318" }}>{verify.error.message}</Text> : null}
      {resend.data ? <Text style={{ color: "#126C57" }}>{resend.data.message}</Text> : null}
      <Pressable disabled={verify.isPending || digits.join("").length !== 6} onPress={() => verify.mutate()} style={{ backgroundColor: "#126C57", padding: 16, borderRadius: 8, alignItems: "center", opacity: verify.isPending ? 0.6 : 1 }}>
        <Text style={{ color: "white", fontWeight: "800" }}>{verify.isPending ? "Verifying..." : "Verify account"}</Text>
      </Pressable>
      <Pressable disabled={resend.isPending} onPress={() => resend.mutate()} style={{ padding: 12, alignItems: "center" }}>
        <Text style={{ color: "#126C57", fontWeight: "700" }}>{resend.isPending ? "Sending..." : "Resend code"}</Text>
      </Pressable>
    </View>
  );
}
