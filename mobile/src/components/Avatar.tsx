import { Ionicons } from "@expo/vector-icons";
import { Image, Text, View } from "react-native";
import { colors } from "../theme/theme";

export function Avatar({ uri, name, size = 44 }: { uri?: string | null; name?: string; size?: number }) {
  if (uri) return <Image source={{ uri }} style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: colors.soft }} />;
  const initial = (name?.trim()?.[0] ?? "M").toUpperCase();
  return (
    <View style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" }}>
      <Text style={{ color: "white", fontSize: Math.max(14, size * 0.38), fontWeight: "800" }}>{initial}</Text>
    </View>
  );
}

export function IconAvatar({ icon, size = 44 }: { icon: keyof typeof Ionicons.glyphMap; size?: number }) {
  return <View style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: colors.soft, alignItems: "center", justifyContent: "center" }}><Ionicons name={icon} size={Math.round(size * 0.5)} color={colors.primary} /></View>;
}