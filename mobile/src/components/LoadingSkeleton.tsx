import { View } from "react-native";
import { colors } from "../theme/theme";

export function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return <View style={{ gap: 14, padding: 18 }}>{Array.from({ length: rows }).map((_, index) => <View key={index} style={{ backgroundColor: colors.background, borderRadius: 18, borderWidth: 1, borderColor: colors.border, padding: 14, gap: 12 }}><View style={{ flexDirection: "row", gap: 10, alignItems: "center" }}><View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: colors.soft }} /><View style={{ gap: 8, flex: 1 }}><View style={{ width: "45%", height: 12, borderRadius: 6, backgroundColor: colors.soft }} /><View style={{ width: "30%", height: 10, borderRadius: 5, backgroundColor: colors.soft }} /></View></View><View style={{ height: 180, borderRadius: 14, backgroundColor: colors.soft }} /><View style={{ width: "70%", height: 12, borderRadius: 6, backgroundColor: colors.soft }} /></View>)}</View>;
}