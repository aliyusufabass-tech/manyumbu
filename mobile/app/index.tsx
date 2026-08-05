import { Link } from "expo-router";
import { Pressable, Text, View } from "react-native";

export default function OnboardingScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: "#F7FBF8", padding: 24, justifyContent: "center", gap: 24 }}>
      <View style={{ width: 72, height: 72, borderRadius: 20, backgroundColor: "#126C57", alignItems: "center", justifyContent: "center" }}>
        <Text style={{ color: "white", fontSize: 28, fontWeight: "800" }}>M</Text>
      </View>
      <View style={{ gap: 10 }}>
        <Text style={{ fontSize: 34, fontWeight: "800", color: "#14231F" }}>Manyumbu</Text>
        <Text style={{ fontSize: 16, color: "#52605B", lineHeight: 24 }}>Share daily moments, join conversations, and stay close through private messaging.</Text>
      </View>
      <View style={{ gap: 12 }}>
        <Link href="/register" asChild>
          <Pressable style={{ backgroundColor: "#126C57", padding: 16, borderRadius: 8, alignItems: "center" }}>
            <Text style={{ color: "white", fontWeight: "700" }}>Create account</Text>
          </Pressable>
        </Link>
        <Link href="/login" asChild>
          <Pressable style={{ borderColor: "#126C57", borderWidth: 1, padding: 16, borderRadius: 8, alignItems: "center" }}>
            <Text style={{ color: "#126C57", fontWeight: "700" }}>Sign in</Text>
          </Pressable>
        </Link>
      </View>
    </View>
  );
}
