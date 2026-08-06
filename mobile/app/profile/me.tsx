import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { Image, Pressable, RefreshControl, SafeAreaView, ScrollView, Text, View } from "react-native";
import { getMyProfile } from "../../src/api/profile";
import { AppHeader } from "../../src/components/AppHeader";
import { Avatar } from "../../src/components/Avatar";
import { EmptyState } from "../../src/components/EmptyState";
import { LoadingSkeleton } from "../../src/components/LoadingSkeleton";
import { PostGrid } from "../../src/components/PostGrid";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { ReelGrid } from "../../src/components/ReelGrid";
import { colors } from "../../src/theme/theme";

function Stat({ label, value }: { label: string; value: number }) {
  return <View style={{ alignItems: "center", flex: 1 }}><Text style={{ color: colors.text, fontSize: 18, fontWeight: "900" }}>{value}</Text><Text style={{ color: colors.muted, marginTop: 2 }}>{label}</Text></View>;
}

export default function MyProfileScreen() {
  const query = useQuery({ queryKey: ["profile", "me"], queryFn: getMyProfile });
  if (query.isLoading) return <SafeAreaView style={{ flex: 1, backgroundColor: colors.soft }}><AppHeader title="Profile" /><LoadingSkeleton rows={2} /></SafeAreaView>;
  if (query.isError || !query.data) return <SafeAreaView style={{ flex: 1, backgroundColor: colors.soft }}><AppHeader title="Profile" /><EmptyState icon="person-circle-outline" title="Profile could not be loaded" actionLabel="Retry" onAction={() => query.refetch()} /></SafeAreaView>;
  const profile = query.data.data.profile;
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.soft }}>
      <AppHeader title="Profile" actions={[{ icon: "settings-outline", label: "Settings", onPress: () => router.push("/profile/settings") }]} />
      <ScrollView refreshControl={<RefreshControl refreshing={query.isFetching} onRefresh={() => query.refetch()} />} contentContainerStyle={{ paddingBottom: 100 }}>
        <View style={{ backgroundColor: colors.background }}>
          <View style={{ height: 126, backgroundColor: "#DDEFEA" }}>{profile.cover_photo ? <Image source={{ uri: profile.cover_photo }} style={{ width: "100%", height: "100%" }} resizeMode="cover" /> : null}</View>
          <View style={{ paddingHorizontal: 18, paddingBottom: 18 }}>
            <View style={{ marginTop: -48, flexDirection: "row", alignItems: "flex-end", justifyContent: "space-between" }}>
              <View style={{ borderWidth: 4, borderColor: colors.background, borderRadius: 54 }}><Avatar uri={profile.profile_picture} name={profile.full_name || profile.username} size={96} /></View>
              <View style={{ flexDirection: "row", gap: 10, marginBottom: 6 }}><PrimaryButton title="Edit" variant="secondary" onPress={() => router.push("/profile/edit")} /><Pressable onPress={() => {}} style={{ width: 52, height: 52, borderRadius: 14, backgroundColor: colors.soft, alignItems: "center", justifyContent: "center" }}><Ionicons name="share-social-outline" size={21} color={colors.text} /></Pressable></View>
            </View>
            <Text style={{ color: colors.text, fontSize: 25, fontWeight: "900", marginTop: 10 }}>{profile.full_name || profile.username} {profile.is_verified ? <Ionicons name="checkmark-circle" size={20} color={colors.primary} /> : null}</Text>
            <Text style={{ color: colors.muted, marginTop: 3 }}>@{profile.username}</Text>
            {profile.bio ? <Text style={{ color: colors.text, lineHeight: 22, marginTop: 12 }}>{profile.bio}</Text> : <Text style={{ color: colors.muted, lineHeight: 22, marginTop: 12 }}>Add a bio so people know what you are about.</Text>}
            <View style={{ flexDirection: "row", paddingVertical: 18, borderTopWidth: 1, borderBottomWidth: 1, borderColor: colors.border, marginTop: 16 }}><Stat label="Posts" value={profile.posts_count} /><Stat label="Followers" value={profile.followers_count} /><Stat label="Following" value={profile.following_count} /></View>
          </View>
        </View>
        <View style={{ padding: 14, gap: 14 }}>
          <View style={{ backgroundColor: colors.background, borderRadius: 18, padding: 14, borderWidth: 1, borderColor: colors.border }}><Text style={{ color: colors.text, fontWeight: "900", fontSize: 17, marginBottom: 12 }}>Posts</Text><PostGrid username={profile.username} /></View>
          <View style={{ backgroundColor: colors.background, borderRadius: 18, padding: 14, borderWidth: 1, borderColor: colors.border }}><Text style={{ color: colors.text, fontWeight: "900", fontSize: 17, marginBottom: 12 }}>Reels</Text><ReelGrid username={profile.username} /></View>
          <Pressable onPress={() => router.push("/posts/saved")} style={{ backgroundColor: colors.background, borderRadius: 18, padding: 16, borderWidth: 1, borderColor: colors.border, flexDirection: "row", alignItems: "center", gap: 12 }}><Ionicons name="bookmark-outline" size={24} color={colors.primary} /><View style={{ flex: 1 }}><Text style={{ color: colors.text, fontWeight: "900" }}>Saved posts</Text><Text style={{ color: colors.muted, marginTop: 3 }}>Private collection only you can see</Text></View><Ionicons name="chevron-forward" size={20} color={colors.muted} /></Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}