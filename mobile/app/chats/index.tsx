import { Ionicons } from "@expo/vector-icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { FlatList, Pressable, SafeAreaView, Text, TextInput, View } from "react-native";
import { conversationAction, listConversations } from "../../src/api/messaging";
import { AppHeader } from "../../src/components/AppHeader";
import { Avatar } from "../../src/components/Avatar";
import { EmptyState } from "../../src/components/EmptyState";
import { LoadingSkeleton } from "../../src/components/LoadingSkeleton";
import { colors } from "../../src/theme/theme";
import type { Conversation } from "../../src/types/messaging";

function timeLabel(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  return sameDay ? date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function ConversationRow({ item, onArchive, onUnread }: { item: Conversation; onArchive: () => void; onUnread: () => void }) {
  const peer = item.peer;
  const preview = item.last_message?.deleted_for_everyone_at ? "Message deleted" : item.last_message?.text || item.last_message?.message_type || "No messages yet";
  return (
    <Pressable onPress={() => router.push({ pathname: "/chats/[id]", params: { id: item.id } })} style={({ pressed }) => ({ padding: 14, backgroundColor: colors.background, borderRadius: 16, borderWidth: 1, borderColor: colors.border, flexDirection: "row", gap: 12, opacity: pressed ? 0.86 : 1 })}>
      <Avatar uri={peer?.profile_picture} name={peer?.full_name || peer?.username || "Manyumbu"} size={54} />
      <View style={{ flex: 1, minWidth: 0 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <Text numberOfLines={1} style={{ flex: 1, color: colors.text, fontWeight: "900", fontSize: 16 }}>{peer?.full_name || peer?.username || "Conversation"} {peer?.is_verified ? <Ionicons name="checkmark-circle" size={14} color={colors.primary} /> : null}</Text>
          <Text style={{ color: colors.muted, fontSize: 12 }}>{timeLabel(item.last_message_at)}</Text>
        </View>
        <Text numberOfLines={1} style={{ color: item.unread_count ? colors.text : colors.muted, marginTop: 4, fontWeight: item.unread_count ? "800" : "500" }}>{item.request_state === "pending" ? "Message request" : preview}</Text>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 12, marginTop: 10 }}>
          <Pressable onPress={onArchive} hitSlop={8}><Text style={{ color: colors.primary, fontWeight: "800" }}>{item.archived ? "Unarchive" : "Archive"}</Text></Pressable>
          <Pressable onPress={onUnread} hitSlop={8}><Text style={{ color: colors.primary, fontWeight: "800" }}>Unread</Text></Pressable>
          {item.muted_until ? <Text style={{ color: colors.muted }}>Muted</Text> : null}
          <View style={{ flex: 1 }} />
          {item.unread_count ? <Text style={{ backgroundColor: colors.primary, color: "white", paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999, overflow: "hidden", fontWeight: "900" }}>{item.unread_count}</Text> : null}
        </View>
      </View>
    </Pressable>
  );
}

export default function ChatsScreen() {
  const [q, setQ] = useState("");
  const [archived, setArchived] = useState(false);
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["conversations", q, archived], queryFn: () => listConversations({ q, archived }) });
  const action = useMutation({ mutationFn: ({ id, name }: { id: string; name: "archive" | "unarchive" | "unread" }) => conversationAction(id, name), onSuccess: () => client.invalidateQueries({ queryKey: ["conversations"] }) });
  const conversations = useMemo(() => query.data?.data.results ?? [], [query.data]);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.soft }}>
      <AppHeader title="Chats" subtitle={archived ? "Archived conversations" : "Messages and requests"} actions={[{ icon: "create-outline", label: "New chat", onPress: () => router.push("/chats/start") }]} />
      <View style={{ padding: 14, gap: 12 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: colors.background, borderRadius: 16, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14 }}>
          <Ionicons name="search-outline" size={20} color={colors.muted} />
          <TextInput value={q} onChangeText={setQ} placeholder="Search conversations" placeholderTextColor={colors.muted} autoCapitalize="none" style={{ flex: 1, height: 50, color: colors.text, fontSize: 16 }} />
          {q ? <Pressable onPress={() => setQ("")}><Ionicons name="close-circle" size={20} color={colors.muted} /></Pressable> : null}
        </View>
        <View style={{ flexDirection: "row", gap: 10 }}>
          <Pressable onPress={() => setArchived(false)} style={{ flex: 1, paddingVertical: 11, borderRadius: 999, backgroundColor: archived ? colors.background : colors.primary, borderWidth: 1, borderColor: archived ? colors.border : colors.primary }}><Text style={{ color: archived ? colors.text : "white", textAlign: "center", fontWeight: "900" }}>Inbox</Text></Pressable>
          <Pressable onPress={() => setArchived(true)} style={{ flex: 1, paddingVertical: 11, borderRadius: 999, backgroundColor: archived ? colors.primary : colors.background, borderWidth: 1, borderColor: archived ? colors.primary : colors.border }}><Text style={{ color: archived ? "white" : colors.text, textAlign: "center", fontWeight: "900" }}>Archived</Text></Pressable>
        </View>
        <View style={{ flexDirection: "row", gap: 10 }}>
          <Pressable onPress={() => router.push("/chats/requests")} style={{ flex: 1, padding: 12, borderRadius: 14, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border }}><Text style={{ color: colors.primary, fontWeight: "900", textAlign: "center" }}>Requests</Text></Pressable>
          <Pressable onPress={() => router.push("/groups")} style={{ flex: 1, padding: 12, borderRadius: 14, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border }}><Text style={{ color: colors.primary, fontWeight: "900", textAlign: "center" }}>Groups</Text></Pressable>
        </View>
      </View>
      {query.isLoading ? <LoadingSkeleton rows={4} /> : null}
      {query.isError ? <EmptyState icon="cloud-offline-outline" title="Chats could not be loaded" message="Check your connection and try again." actionLabel="Retry" onAction={() => query.refetch()} /> : null}
      {!query.isLoading && !query.isError ? (
        <FlatList
          data={conversations}
          keyExtractor={(item) => item.id}
          refreshing={query.isFetching}
          onRefresh={() => query.refetch()}
          contentContainerStyle={{ padding: 14, gap: 12, paddingBottom: 90 }}
          ListEmptyComponent={<EmptyState icon="chatbubble-ellipses-outline" title={q ? "No conversations found" : "No conversations yet"} message={q ? "Try another name or username." : "Start a private chat or reply to message requests."} actionLabel="New chat" onAction={() => router.push("/chats/start")} />}
          renderItem={({ item }) => <ConversationRow item={item} onArchive={() => action.mutate({ id: item.id, name: item.archived ? "unarchive" : "archive" })} onUnread={() => action.mutate({ id: item.id, name: "unread" })} />}
        />
      ) : null}
    </SafeAreaView>
  );
}
