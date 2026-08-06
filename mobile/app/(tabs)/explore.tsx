import { Ionicons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { FlatList, Pressable, SafeAreaView, Text, TextInput, View } from "react-native";
import { follow, searchProfiles, unfollow } from "../../src/api/profile";
import { AppHeader } from "../../src/components/AppHeader";
import { EmptyState } from "../../src/components/EmptyState";
import { LoadingSkeleton } from "../../src/components/LoadingSkeleton";
import { PostCard } from "../../src/components/PostCard";
import { UserCard } from "../../src/components/UserCard";
import { colors } from "../../src/theme/theme";
import type { CompactUser } from "../../src/types/profile";

type Tab = "People" | "Posts" | "Trending";
const tabs: Tab[] = ["People", "Posts", "Trending"];

export default function ExploreScreen() {
  const [q, setQ] = useState("");
  const [tab, setTab] = useState<Tab>("People");
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["profiles", "search", q], queryFn: () => searchProfiles(q), enabled: tab === "People" });
  const followMutation = useMutation({ mutationFn: async (user: CompactUser): Promise<unknown> => user.is_following ? unfollow(user.username) : follow(user.username), onSuccess: () => client.invalidateQueries({ queryKey: ["profiles", "search"] }) });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.soft }}>
      <AppHeader title="Explore" subtitle="Find people, posts, and trends" />
      <View style={{ padding: 14, gap: 12 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: colors.background, borderRadius: 16, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14 }}>
          <Ionicons name="search-outline" size={20} color={colors.muted} />
          <TextInput value={q} onChangeText={setQ} placeholder="Search users" placeholderTextColor={colors.muted} autoCapitalize="none" style={{ flex: 1, height: 50, color: colors.text, fontSize: 16 }} />
          {q ? <Pressable onPress={() => setQ("")}><Ionicons name="close-circle" size={20} color={colors.muted} /></Pressable> : null}
        </View>
        <View style={{ flexDirection: "row", gap: 8 }}>
          {tabs.map((item) => <Pressable key={item} onPress={() => setTab(item)} style={{ flex: 1, paddingVertical: 11, borderRadius: 999, backgroundColor: tab === item ? colors.primary : colors.background, borderWidth: 1, borderColor: tab === item ? colors.primary : colors.border }}><Text style={{ color: tab === item ? "white" : colors.text, textAlign: "center", fontWeight: "800" }}>{item}</Text></Pressable>)}
        </View>
      </View>
      {tab === "People" ? (
        query.isLoading ? <LoadingSkeleton rows={3} /> : <FlatList data={query.data?.data.results ?? []} keyExtractor={(item) => item.username} contentContainerStyle={{ padding: 14, gap: 12, paddingBottom: 90 }} refreshing={query.isFetching} onRefresh={() => query.refetch()} ListEmptyComponent={<EmptyState icon="people-outline" title={q ? "No users found" : "Search for people"} message={q ? "Try a different username, phone, or name." : "Discover creators, friends, and communities on Manyumbu."} />} renderItem={({ item }) => <UserCard user={item} onPress={() => router.push({ pathname: "/profile/[username]", params: { username: item.username } })} onFollow={() => followMutation.mutate(item)} />} />
      ) : tab === "Posts" ? <EmptyState icon="grid-outline" title="Post discovery is coming together" message="Use search for people now; post search can plug into the existing API when available." /> : <EmptyState icon="flame-outline" title="No trends yet" message="Trending hashtags and reels will appear here as people create more content." />}
    </SafeAreaView>
  );
}
