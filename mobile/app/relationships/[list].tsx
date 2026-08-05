import { useQuery } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { RefreshControl, Text, View } from "react-native";
import { relationshipList } from "../../src/api/profile";
import { ScreenState, UserList } from "../../src/components/UserList";

const supported = ["followers", "following", "requests-received", "requests-sent", "suggested"] as const;
type ListName = typeof supported[number];

export default function RelationshipListScreen() {
  const { list } = useLocalSearchParams<{ list: string }>();
  const name = supported.includes(list as ListName) ? (list as ListName) : "followers";
  const query = useQuery({ queryKey: ["relationships", name], queryFn: () => relationshipList(name) });
  if (query.isLoading) return <ScreenState text="Loading people..." />;
  if (!query.data) return <ScreenState text="People could not be loaded." />;
  return (
    <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 20, paddingTop: 56 }}>
      <Text style={{ fontSize: 26, fontWeight: "800", marginBottom: 12 }}>{name.replaceAll("-", " ")}</Text>
      <UserList users={query.data.data.results} emptyText="Nothing here yet." onPress={(user) => router.push({ pathname: "/profile/[username]", params: { username: user.username } })} />
    </View>
  );
}
