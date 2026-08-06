import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";
import { colors } from "../../src/theme/theme";

type TabName = "home" | "explore" | "create" | "reels" | "profile";
const icons: Record<TabName, keyof typeof Ionicons.glyphMap> = {
  home: "home-outline",
  explore: "search-outline",
  create: "add-circle-outline",
  reels: "film-outline",
  profile: "person-circle-outline",
};

export default function TabsLayout() {
  return (
    <Tabs screenOptions={({ route }) => ({
      headerShown: false,
      tabBarActiveTintColor: colors.primary,
      tabBarInactiveTintColor: colors.muted,
      tabBarStyle: { height: 64, paddingTop: 7, paddingBottom: 9, borderTopColor: colors.border, backgroundColor: colors.background },
      tabBarLabelStyle: { fontWeight: "700", fontSize: 12 },
      tabBarIcon: ({ color, size }) => <Ionicons name={icons[route.name as TabName] ?? "ellipse-outline"} color={color} size={route.name === "create" ? size + 5 : size} />,
    })}>
      <Tabs.Screen name="home" options={{ title: "Home" }} />
      <Tabs.Screen name="explore" options={{ title: "Explore" }} />
      <Tabs.Screen name="create" options={{ title: "Create" }} />
      <Tabs.Screen name="reels" options={{ title: "Reels" }} />
      <Tabs.Screen name="profile" options={{ title: "Profile" }} />
      <Tabs.Screen name="chats" options={{ href: null }} />
    </Tabs>
  );
}