import { useQuery } from "@tanstack/react-query";
import { Text, View } from "react-native";
import { simpleRelationshipList } from "../../src/api/profile";
import { ScreenState, UserList } from "../../src/components/UserList";

export default function CloseFriendsScreen() {
  const query = useQuery({ queryKey: ["close-friends"], queryFn: () => simpleRelationshipList("close-friends") });
  if (query.isLoading) return <ScreenState text="Loading close friends..." />;
  if (!query.data) return <ScreenState text="Close friends could not be loaded." />;
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 20, paddingTop: 56 }}><Text style={{ fontSize: 26, fontWeight: "800", marginBottom: 12 }}>Close friends</Text><UserList users={query.data.data.results} emptyText="No close friends yet." /></View>;
}
