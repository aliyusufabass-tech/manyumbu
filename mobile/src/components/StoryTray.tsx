import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { FlatList, Pressable, Text, View } from "react-native";
import { getStoryTray } from "../api/phase4";
import type { Story } from "../types/phase4";
import { colors } from "../theme/theme";
import { Avatar } from "./Avatar";

type TrayItem = Story | { id: "create"; create: true };

export function StoryTray() {
  const query = useQuery({ queryKey: ["stories", "tray"], queryFn: getStoryTray });
  const stories: TrayItem[] = [{ id: "create", create: true }, ...(query.data?.data.results ?? [])];
  return (
    <View style={{ paddingVertical: 14 }}>
      <FlatList
        horizontal
        data={stories}
        keyExtractor={(item) => item.id}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ gap: 12, paddingHorizontal: 2 }}
        renderItem={({ item }) => {
          if ("create" in item) {
            return <Pressable onPress={() => router.push("/stories/create")} style={{ width: 78, alignItems: "center", gap: 7 }}><View style={{ width: 64, height: 64, borderRadius: 32, backgroundColor: colors.soft, alignItems: "center", justifyContent: "center" }}><View style={{ width: 34, height: 34, borderRadius: 17, backgroundColor: colors.primary, alignItems: "center", justifyContent: "center" }}><Ionicons name="add" size={22} color="white" /></View></View><Text numberOfLines={1} style={{ color: colors.text, fontSize: 12, fontWeight: "700" }}>Your story</Text></Pressable>;
          }
          return <Pressable onPress={() => router.push({ pathname: "/stories/[id]", params: { id: item.id } })} style={{ width: 78, alignItems: "center", gap: 7 }}><View style={{ width: 68, height: 68, borderRadius: 34, borderWidth: 3, borderColor: item.viewer_has_viewed ? colors.border : colors.primary, alignItems: "center", justifyContent: "center" }}><Avatar uri={item.author.profile_picture} name={item.author.username} size={58} /></View><Text numberOfLines={1} style={{ color: colors.text, fontSize: 12 }}>{item.author.username}</Text></Pressable>;
        }}
      />
    </View>
  );
}