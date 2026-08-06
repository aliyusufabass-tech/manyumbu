import { Ionicons } from "@expo/vector-icons";
import { Text, View } from "react-native";
import { colors } from "../theme/theme";
import { PrimaryButton } from "./PrimaryButton";

export function EmptyState({ icon = "sparkles-outline", title, message, actionLabel, onAction }: { icon?: keyof typeof Ionicons.glyphMap; title: string; message?: string; actionLabel?: string; onAction?: () => void }) {
  return <View style={{ alignItems: "center", justifyContent: "center", padding: 28, gap: 12 }}><View style={{ width: 72, height: 72, borderRadius: 36, backgroundColor: colors.soft, alignItems: "center", justifyContent: "center" }}><Ionicons name={icon} size={32} color={colors.primary} /></View><Text style={{ color: colors.text, fontWeight: "900", fontSize: 18, textAlign: "center" }}>{title}</Text>{message ? <Text style={{ color: colors.muted, textAlign: "center", lineHeight: 21 }}>{message}</Text> : null}{actionLabel ? <View style={{ minWidth: 170, marginTop: 4 }}><PrimaryButton title={actionLabel} onPress={onAction} /></View> : null}</View>;
}