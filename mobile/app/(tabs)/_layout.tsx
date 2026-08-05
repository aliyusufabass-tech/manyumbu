import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";

type TabName = "home" | "explore" | "create" | "reels" | "chats";
const icons: Record<TabName, keyof typeof Ionicons.glyphMap> = {
  home: "home-outline",
  explore: "search-outline",
  create: "add-circle-outline",
  reels: "film-outline",
  chats: "chatbubbles-outline",
};

export default function TabsLayout() {
  return (
    <Tabs screenOptions={({ route }) => ({
      tabBarActiveTintColor: "#126C57",
      headerShown: false,
      tabBarIcon: ({ color, size }) => <Ionicons name={icons[route.name as TabName]} color={color} size={size} />,
    })} />
  );
}
