import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { Alert, Pressable, ScrollView, Text } from "react-native";
import { block, follow, getProfile, unfollow } from "../../src/api/profile";
import { ProfileCard } from "../../src/components/ProfileCard";
import { PostGrid } from "../../src/components/PostGrid";
import { ScreenState } from "../../src/components/UserList";

export default function OtherProfileScreen() {
  const { username } = useLocalSearchParams<{ username: string }>();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["profile", username], queryFn: () => getProfile(username ?? ""), enabled: !!username });
  const followMutation = useMutation({ mutationFn: () => follow(username ?? ""), onSuccess: () => client.invalidateQueries({ queryKey: ["profile", username] }) });
  const unfollowMutation = useMutation({ mutationFn: () => unfollow(username ?? ""), onSuccess: () => client.invalidateQueries({ queryKey: ["profile", username] }) });
  const blockMutation = useMutation({ mutationFn: () => block(username ?? ""), onSuccess: () => client.invalidateQueries({ queryKey: ["profile"] }) });
  if (query.isLoading) return <ScreenState text="Loading profile..." />;
  if (query.isError || !query.data) return <ScreenState text="Profile could not be loaded." />;
  const profile = query.data.data.profile;
  return (
    <ScrollView contentContainerStyle={{ padding: 20, paddingTop: 56, gap: 16 }} style={{ backgroundColor: "#FFFFFF" }}>
      <ProfileCard profile={profile} />
      <Pressable onPress={() => profile.is_following ? unfollowMutation.mutate() : followMutation.mutate()} style={{ backgroundColor: "#126C57", padding: 14, borderRadius: 8, alignItems: "center" }}><Text style={{ color: "white", fontWeight: "800" }}>{profile.is_following ? "Unfollow" : profile.is_private ? "Request follow" : "Follow"}</Text></Pressable>
      <Pressable onPress={() => Alert.alert("Block user", "Block this user and remove relationships?", [{ text: "Cancel" }, { text: "Block", style: "destructive", onPress: () => blockMutation.mutate() }])} style={{ borderWidth: 1, borderColor: "#B42318", padding: 14, borderRadius: 8, alignItems: "center" }}><Text style={{ color: "#B42318", fontWeight: "800" }}>Block</Text></Pressable>
      <Text style={{ fontWeight: "800", fontSize: 18 }}>Posts</Text>{profile.viewer_can_view_private_content ? <PostGrid username={profile.username} /> : <Text style={{ color: "#52605B" }}>Follow this private account to see posts.</Text>}
    </ScrollView>
  );
}

