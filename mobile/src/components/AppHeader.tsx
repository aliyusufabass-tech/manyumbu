import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { colors } from "../theme/theme";

export function AppHeader({ title = "Manyumbu", subtitle, showBack, actions = [] }: { title?: string; subtitle?: string; showBack?: boolean; actions?: Array<{ icon: keyof typeof Ionicons.glyphMap; onPress: () => void; label?: string }> }) {
  return (
    <View style={{ paddingHorizontal: 18, paddingTop: 10, paddingBottom: 12, backgroundColor: colors.background, borderBottomWidth: 1, borderBottomColor: colors.border, flexDirection: "row", alignItems: "center", gap: 12 }}>
      {showBack ? <Pressable onPress={() => router.back()} hitSlop={12}><Ionicons name="chevron-back" size={26} color={colors.text} /></Pressable> : null}
      <View style={{ flex: 1 }}>
        <Text style={{ fontSize: title === "Manyumbu" ? 28 : 22, fontWeight: "900", color: colors.text }}>{title}</Text>
        {subtitle ? <Text style={{ color: colors.muted, marginTop: 2 }}>{subtitle}</Text> : null}
      </View>
      {actions.map((action, index) => <Pressable key={`${action.icon}-${index}`} accessibilityLabel={action.label} onPress={action.onPress} hitSlop={12} style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: colors.soft, alignItems: "center", justifyContent: "center" }}><Ionicons name={action.icon} size={21} color={colors.text} /></Pressable>)}
    </View>
  );
}