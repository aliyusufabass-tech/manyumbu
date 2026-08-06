import { Ionicons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";
import { colors } from "../theme/theme";

export function SettingsRow({ icon, title, subtitle, danger, onPress, value }: { icon: keyof typeof Ionicons.glyphMap; title: string; subtitle?: string; danger?: boolean; onPress?: () => void; value?: string }) {
  return <Pressable onPress={onPress} style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 14, opacity: pressed ? 0.75 : 1 })}><View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: danger ? "#FEF3F2" : colors.soft, alignItems: "center", justifyContent: "center" }}><Ionicons name={icon} size={20} color={danger ? colors.error : colors.primary} /></View><View style={{ flex: 1 }}><Text style={{ color: danger ? colors.error : colors.text, fontWeight: "800", fontSize: 16 }}>{title}</Text>{subtitle ? <Text style={{ color: colors.muted, marginTop: 2 }}>{subtitle}</Text> : null}</View>{value ? <Text style={{ color: colors.muted }}>{value}</Text> : null}<Ionicons name="chevron-forward" size={18} color={colors.muted} /></Pressable>;
}