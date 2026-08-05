import { Link } from "expo-router";
import { Text, View } from "react-native";

export default function AccountSettingsScreen() {
  return (
    <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 24, paddingTop: 64, gap: 16 }}>
      <Text style={{ fontSize: 28, fontWeight: "800" }}>Account settings</Text>
      <Link href="/profile/privacy"><Text style={{ color: "#126C57", fontWeight: "800" }}>Privacy settings</Text></Link>
      <Link href="/relationships/blocked"><Text style={{ color: "#126C57", fontWeight: "800" }}>Blocked users</Text></Link>
      <Link href="/relationships/restricted"><Text style={{ color: "#126C57", fontWeight: "800" }}>Restricted users</Text></Link>
      <Link href="/relationships/muted"><Text style={{ color: "#126C57", fontWeight: "800" }}>Muted users</Text></Link>
      <Link href="/relationships/close-friends"><Text style={{ color: "#126C57", fontWeight: "800" }}>Close friends</Text></Link>
    </View>
  );
}
