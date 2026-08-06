import { ActivityIndicator, Pressable, Text } from "react-native";
import { colors } from "../theme/theme";

export function PrimaryButton({ title, onPress, loading, disabled, variant = "primary" }: { title: string; onPress?: () => void; loading?: boolean; disabled?: boolean; variant?: "primary" | "secondary" | "danger" }) {
  const bg = variant === "primary" ? colors.primary : variant === "danger" ? colors.error : colors.soft;
  const fg = variant === "secondary" ? colors.text : "white";
  return <Pressable disabled={disabled || loading} onPress={onPress} style={({ pressed }) => ({ minHeight: 52, borderRadius: 14, backgroundColor: bg, opacity: disabled ? 0.5 : pressed ? 0.86 : 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 18 })}>{loading ? <ActivityIndicator color={fg} /> : <Text style={{ color: fg, fontWeight: "800", fontSize: 16 }}>{title}</Text>}</Pressable>;
}