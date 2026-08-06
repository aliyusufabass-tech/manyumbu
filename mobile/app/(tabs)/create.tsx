import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { Pressable, SafeAreaView, Text, View } from "react-native";
import { AppHeader } from "../../src/components/AppHeader";
import { colors } from "../../src/theme/theme";

type CreateItem = { title: string; description: string; icon: keyof typeof Ionicons.glyphMap; route?: string; disabled?: boolean };
const items: CreateItem[] = [
  { title: "Create post", description: "Share photos, videos, captions, hashtags, and mentions.", icon: "images-outline", route: "/posts/create" },
  { title: "Create story", description: "Post a quick moment with audience controls.", icon: "add-circle-outline", route: "/stories/create" },
  { title: "Create reel", description: "Upload a vertical video for the reels feed.", icon: "film-outline", route: "/reels/create" },
  { title: "Go live", description: "Live video is not enabled for this build yet.", icon: "radio-outline", disabled: true },
];

export default function CreateScreen() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.soft }}>
      <AppHeader title="Create" subtitle="Choose what you want to share" />
      <View style={{ padding: 16, gap: 12 }}>
        {items.map((item) => <Pressable key={item.title} disabled={item.disabled} onPress={() => item.route && router.push(item.route)} style={({ pressed }) => ({ backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border, borderRadius: 18, padding: 16, flexDirection: "row", gap: 14, alignItems: "center", opacity: item.disabled ? 0.55 : pressed ? 0.86 : 1 })}>
          <View style={{ width: 52, height: 52, borderRadius: 18, backgroundColor: item.disabled ? colors.soft : "#E8F5F1", alignItems: "center", justifyContent: "center" }}><Ionicons name={item.icon} size={26} color={item.disabled ? colors.muted : colors.primary} /></View>
          <View style={{ flex: 1 }}><Text style={{ color: colors.text, fontSize: 17, fontWeight: "900" }}>{item.title}</Text><Text style={{ color: colors.muted, lineHeight: 20, marginTop: 3 }}>{item.description}</Text></View>
          <Ionicons name="chevron-forward" size={20} color={colors.muted} />
        </Pressable>)}
      </View>
    </SafeAreaView>
  );
}