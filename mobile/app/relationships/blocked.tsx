import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { Text, View } from "react-native";
import { simpleRelationshipList } from "../../src/api/profile";
import { ScreenState, UserList } from "../../src/components/UserList";

export default function BlockedUsersScreen() {
  const query = useQuery({ queryKey: ["blocked"], queryFn: () => simpleRelationshipList("blocked") });
  if (query.isLoading) return <ScreenState text="Loading blocked users..." />;
  if (!query.data) return <ScreenState text="Blocked users could not be loaded." />;
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 20, paddingTop: 56 }}><Text style={{ fontSize: 26, fontWeight: "800", marginBottom: 12 }}>Blocked users</Text><UserList users={query.data.data.results} emptyText="No blocked users." onPress={(user) => router.push({ pathname: "/profile/[username]", params: { username: user.username } })} /></View>;
}
