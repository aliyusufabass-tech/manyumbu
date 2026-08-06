import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SafeAreaView, Switch, Text, View } from "react-native";
import { getNotificationPreferences, updateNotificationPreferences } from "../../src/api/groups";
import { AppHeader } from "../../src/components/AppHeader";
import { ScreenState } from "../../src/components/UserList";
import { colors } from "../../src/theme/theme";

const rows = [
  ["Message notifications", ["private_messages", "message_requests"]],
  ["Follow notifications", ["followers"]],
  ["Post notifications", ["likes", "comments", "story_reactions", "reel_activity"]],
  ["Group notifications", ["group_messages", "group_role_changes"]],
  ["Mention notifications", ["group_mentions"]],
  ["Call notifications", ["incoming_calls", "missed_calls", "declined_calls", "group_calls"]],
] as const;

export default function NotificationSettingsScreen() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["notification-preferences"], queryFn: getNotificationPreferences });
  const mutation = useMutation({ mutationFn: updateNotificationPreferences, onSuccess: () => client.invalidateQueries({ queryKey: ["notification-preferences"] }) });
  if (query.isLoading) return <ScreenState text="Loading notification settings..." />;
  const prefs = query.data?.data.preferences ?? {};
  return <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}><AppHeader title="Notifications" showBack /><View style={{ padding: 18 }}>{rows.map(([label, keys]) => { const enabled = keys.every((key) => Boolean(prefs[key])); return <View key={label} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 14, borderBottomWidth: 1, borderColor: colors.border }}><Text style={{ color: colors.text, fontWeight: "800" }}>{label}</Text><Switch value={enabled} onValueChange={(value) => mutation.mutate(Object.fromEntries(keys.map((key) => [key, value])))} /></View>; })}</View></SafeAreaView>;
}
