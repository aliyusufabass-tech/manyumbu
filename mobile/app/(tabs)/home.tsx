import { Ionicons } from "@expo/vector-icons";
import { Text, View } from "react-native";

export default function HomeScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 20, paddingTop: 56, gap: 24 }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <Text style={{ fontSize: 26, fontWeight: "800", color: "#14231F" }}>Manyumbu</Text>
        <View style={{ flexDirection: "row", gap: 16 }}>
          <Ionicons name="search-outline" size={24} color="#14231F" />
          <Ionicons name="notifications-outline" size={24} color="#14231F" />
        </View>
      </View>
      <View style={{ backgroundColor: "#EAF4EF", borderRadius: 8, padding: 18, gap: 8 }}>
        <Text style={{ fontWeight: "800", fontSize: 18, color: "#14231F" }}>Home navigation shell</Text>
        <Text style={{ color: "#52605B", lineHeight: 22 }}>Your verified account can now enter the Phase 1 app shell. Feed, stories, reels, and chats start in later phases.</Text>
      </View>
    </View>
  );
}
