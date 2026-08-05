import { useQuery } from "@tanstack/react-query";
import { Text, View } from "react-native";
import { simpleRelationshipList } from "../../src/api/profile";
import { ScreenState, UserList } from "../../src/components/UserList";

export default function RestrictedUsersScreen() {
  const query = useQuery({ queryKey: ["restricted"], queryFn: () => simpleRelationshipList("restricted") });
  if (query.isLoading) return <ScreenState text="Loading restricted users..." />;
  if (!query.data) return <ScreenState text="Restricted users could not be loaded." />;
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 20, paddingTop: 56 }}><Text style={{ fontSize: 26, fontWeight: "800", marginBottom: 12 }}>Restricted users</Text><UserList users={query.data.data.results} emptyText="No restricted users." /></View>;
}
