import { useQuery } from "@tanstack/react-query";
import { Text, View } from "react-native";
import { simpleRelationshipList } from "../../src/api/profile";
import { ScreenState, UserList } from "../../src/components/UserList";

export default function MutedUsersScreen() {
  const query = useQuery({ queryKey: ["muted"], queryFn: () => simpleRelationshipList("muted") });
  if (query.isLoading) return <ScreenState text="Loading muted users..." />;
  if (!query.data) return <ScreenState text="Muted users could not be loaded." />;
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 20, paddingTop: 56 }}><Text style={{ fontSize: 26, fontWeight: "800", marginBottom: 12 }}>Muted users</Text><UserList users={query.data.data.results} emptyText="No muted users." /></View>;
}
