import { router, useLocalSearchParams } from "expo-router";
import { Pressable, Text, View } from "react-native";

export default function CallEndedScreen() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", alignItems: "center", justifyContent: "center", padding: 24 }}><Text style={{ fontSize: 28, fontWeight: "900" }}>Call ended</Text><Text style={{ color: "#6B7280", marginTop: 8 }}>{id ? `Call ${id}` : "The call has finished."}</Text><Pressable onPress={() => router.replace("/calls")} style={{ backgroundColor: "#126C57", padding: 14, borderRadius: 8, marginTop: 20 }}><Text style={{ color: "white", fontWeight: "900" }}>Back to history</Text></Pressable></View>;
}
