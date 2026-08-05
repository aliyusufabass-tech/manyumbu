import { useQuery } from "@tanstack/react-query";
import { Link } from "expo-router";
import { RefreshControl, ScrollView, Text, View } from "react-native";
import { getMyProfile } from "../../src/api/profile";
import { ProfileCard } from "../../src/components/ProfileCard";
import { PostGrid } from "../../src/components/PostGrid";
import { ReelGrid } from "../../src/components/ReelGrid";
import { ScreenState } from "../../src/components/UserList";

export default function MyProfileScreen() {
  const query = useQuery({ queryKey: ["profile", "me"], queryFn: getMyProfile });
  if (query.isLoading) return <ScreenState text="Loading profile..." />;
  if (query.isError || !query.data) return <ScreenState text="Profile could not be loaded." />;
  const profile = query.data.data.profile;
  return (
    <ScrollView style={{ flex: 1, backgroundColor: "#FFFFFF" }} contentContainerStyle={{ padding: 20, paddingTop: 56, gap: 20 }} refreshControl={<RefreshControl refreshing={query.isFetching} onRefresh={() => query.refetch()} />}>
      <ProfileCard profile={profile} />
      <View style={{ flexDirection: "row", gap: 12, flexWrap: "wrap" }}>
        <Link href="/profile/edit"><Text style={{ color: "#126C57", fontWeight: "800" }}>Edit profile</Text></Link>
        <Link href="/relationships/followers"><Text style={{ color: "#126C57", fontWeight: "800" }}>Followers</Text></Link>
        <Link href="/relationships/following"><Text style={{ color: "#126C57", fontWeight: "800" }}>Following</Text></Link>
        <Link href="/profile/privacy"><Text style={{ color: "#126C57", fontWeight: "800" }}>Privacy</Text></Link>
      </View>
      <View style={{ borderWidth: 1, borderColor: "#E2ECE7", borderRadius: 8, padding: 12 }}><Text style={{ fontWeight: "800", marginBottom: 8 }}>Posts</Text><PostGrid username={profile.username} /></View><View style={{ borderWidth: 1, borderColor: "#E2ECE7", borderRadius: 8, padding: 12 }}><Text style={{ fontWeight: "800", marginBottom: 8 }}>Reels</Text><ReelGrid username={profile.username} /></View><View style={{ borderWidth: 1, borderColor: "#E2ECE7", borderRadius: 8, padding: 16 }}><Text style={{ fontWeight: "800" }}>Saved</Text><Link href="/posts/saved"><Text style={{ color: "#126C57", marginTop: 6 }}>Open saved posts</Text></Link></View>
    </ScrollView>
  );
}


