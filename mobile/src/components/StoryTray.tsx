import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { FlatList, Pressable, Text, View } from "react-native";
import { getStoryTray } from "../api/phase4";
import type { Story } from "../types/phase4";

type TrayItem = Story | { id: "create"; create: true };

export function StoryTray() {
  const query = useQuery({ queryKey: ["stories", "tray"], queryFn: getStoryTray });
  const stories: TrayItem[] = [{ id: "create", create: true }, ...(query.data?.data.results ?? [])];
  return (
    <View style={{ paddingVertical: 12 }}>
      <FlatList
        horizontal
        data={stories}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => {
          if ("create" in item) {
            return <Pressable onPress={() => router.push("/stories/create")} style={{ width: 74, alignItems: "center", gap: 6 }}><View style={{ width: 58, height: 58, borderRadius: 29, backgroundColor: "#126C57", alignItems: "center", justifyContent: "center" }}><Text style={{ color: "white", fontSize: 24 }}>+</Text></View><Text>Create</Text></Pressable>;
          }
          return <Pressable onPress={() => router.push({ pathname: "/stories/[id]", params: { id: item.id } })} style={{ width: 82, alignItems: "center", gap: 6 }}><View style={{ width: 58, height: 58, borderRadius: 29, borderWidth: 3, borderColor: item.viewer_has_viewed ? "#AAB8B1" : "#126C57", backgroundColor: "#EAF4EF" }} /><Text numberOfLines={1}>{item.author.username}</Text></Pressable>;
        }}
      />
    </View>
  );
}
