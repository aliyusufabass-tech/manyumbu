import { Image, Text, View } from "react-native";
import type { Profile } from "../types/profile";

export function ProfileCard({ profile }: { profile: Profile }) {
  const avatar = profile.profile_picture ? { uri: profile.profile_picture } : undefined;
  return (
    <View style={{ gap: 14 }}>
      <View style={{ height: 112, borderRadius: 8, backgroundColor: "#DDEBE5", overflow: "hidden" }}>
        {profile.cover_photo ? <Image source={{ uri: profile.cover_photo }} style={{ width: "100%", height: "100%" }} /> : null}
      </View>
      <View style={{ flexDirection: "row", gap: 14, alignItems: "center" }}>
        <View style={{ width: 72, height: 72, borderRadius: 36, backgroundColor: "#126C57", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
          {avatar ? <Image source={avatar} style={{ width: 72, height: 72 }} /> : <Text style={{ color: "white", fontWeight: "800", fontSize: 28 }}>{profile.full_name.slice(0, 1)}</Text>}
        </View>
        <View style={{ flex: 1 }}>
          <Text style={{ fontSize: 22, fontWeight: "800", color: "#14231F" }}>{profile.full_name}{profile.is_verified ? " ?" : ""}</Text>
          <Text style={{ color: "#52605B" }}>@{profile.username} · {profile.account_type}</Text>
        </View>
      </View>
      <Text style={{ color: "#14231F", lineHeight: 22 }}>{profile.bio || "No bio yet."}</Text>
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        <Text>{profile.followers_count} followers</Text>
        <Text>{profile.following_count} following</Text>
        <Text>{profile.posts_count} posts</Text>
        <Text>{profile.reels_count} reels</Text>
      </View>
    </View>
  );
}
