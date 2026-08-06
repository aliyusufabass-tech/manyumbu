import { Ionicons } from "@expo/vector-icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { FlatList, KeyboardAvoidingView, Platform, Pressable, SafeAreaView, Text, TextInput, View } from "react-native";
import { startConversation } from "../../src/api/messaging";
import { searchProfiles } from "../../src/api/profile";
import { AppHeader } from "../../src/components/AppHeader";
import { EmptyState } from "../../src/components/EmptyState";
import { LoadingSkeleton } from "../../src/components/LoadingSkeleton";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { UserCard } from "../../src/components/UserCard";
import { colors } from "../../src/theme/theme";
import type { CompactUser } from "../../src/types/profile";

export default function StartChatScreen() {
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<CompactUser | null>(null);
  const [initial, setInitial] = useState("");
  const users = useQuery({ queryKey: ["profiles", "chat-search", q], queryFn: () => searchProfiles(q), enabled: q.trim().length > 0 });
  const mutation = useMutation({
    mutationFn: () => startConversation(selected?.username ?? "", initial.trim()),
    onSuccess: (result) => router.replace({ pathname: "/chats/[id]", params: { id: result.data.conversation.id } }),
  });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.soft }}>
      <AppHeader title="New chat" subtitle="Search people and start a conversation" showBack />
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
        <View style={{ padding: 14, gap: 12 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: colors.background, borderRadius: 16, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14 }}>
            <Ionicons name="search-outline" size={20} color={colors.muted} />
            <TextInput value={q} onChangeText={(value) => { setQ(value); setSelected(null); }} placeholder="Search by name or username" placeholderTextColor={colors.muted} autoCapitalize="none" style={{ flex: 1, height: 50, color: colors.text, fontSize: 16 }} />
            {q ? <Pressable onPress={() => { setQ(""); setSelected(null); }}><Ionicons name="close-circle" size={20} color={colors.muted} /></Pressable> : null}
          </View>
          {selected ? (
            <View style={{ backgroundColor: colors.background, borderRadius: 16, borderWidth: 1, borderColor: colors.border, padding: 14, gap: 12 }}>
              <Text style={{ color: colors.muted, fontWeight: "900", textTransform: "uppercase", fontSize: 12 }}>Selected</Text>
              <UserCard user={selected} actionLabel="Change" onAction={() => setSelected(null)} onPress={() => router.push({ pathname: "/profile/[username]", params: { username: selected.username } })} />
              <TextInput value={initial} onChangeText={setInitial} placeholder="Optional first message" placeholderTextColor={colors.muted} multiline style={{ minHeight: 92, borderWidth: 1, borderColor: colors.border, borderRadius: 14, padding: 12, color: colors.text, textAlignVertical: "top", backgroundColor: colors.soft }} />
              {mutation.isError ? <Text style={{ color: colors.error }}>{mutation.error.message}</Text> : null}
              <PrimaryButton title="Start chat" loading={mutation.isPending} disabled={mutation.isPending} onPress={() => mutation.mutate()} />
            </View>
          ) : null}
        </View>
        {!selected && users.isLoading ? <LoadingSkeleton rows={3} /> : null}
        {!selected ? (
          <FlatList
            data={users.data?.data.results ?? []}
            keyExtractor={(item) => item.username}
            keyboardShouldPersistTaps="handled"
            contentContainerStyle={{ padding: 14, gap: 12, paddingBottom: 90 }}
            ListEmptyComponent={<EmptyState icon="people-outline" title={q.trim() ? "No users found" : "Find someone to message"} message={q.trim() ? "Try a different name or username." : "Search for an existing Manyumbu user to start or reopen a conversation."} />}
            renderItem={({ item }) => <UserCard user={item} actionLabel="Chat" onAction={() => setSelected(item)} onPress={() => router.push({ pathname: "/profile/[username]", params: { username: item.username } })} />}
          />
        ) : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
