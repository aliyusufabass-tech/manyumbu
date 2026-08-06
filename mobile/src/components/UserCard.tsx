import { Ionicons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";
import type { CompactUser } from "../types/profile";
import { colors } from "../theme/theme";
import { Avatar } from "./Avatar";

export function UserCard({
  user,
  onPress,
  onFollow,
  actionLabel,
  onAction,
}: {
  user: CompactUser;
  onPress?: () => void;
  onFollow?: () => void;
  actionLabel?: string;
  onAction?: () => void;
}) {
  const label = actionLabel ?? (user.is_following ? "Following" : "Follow");
  const action = onAction ?? onFollow;
  const secondary = user.is_following && !actionLabel;
  return (
    <Pressable onPress={onPress} style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 12, padding: 14, backgroundColor: colors.background, borderRadius: 16, borderWidth: 1, borderColor: colors.border, opacity: pressed ? 0.86 : 1 })}>
      <Avatar uri={user.profile_picture} name={user.full_name || user.username} size={52} />
      <View style={{ flex: 1 }}>
        <Text style={{ color: colors.text, fontWeight: "900", fontSize: 16 }}>{user.full_name || user.username} {user.is_verified ? <Ionicons name="checkmark-circle" size={14} color={colors.primary} /> : null}</Text>
        <Text style={{ color: colors.muted }}>@{user.username}</Text>
        <Text style={{ color: colors.muted, marginTop: 3 }} numberOfLines={1}>{user.mutual_followers_count ? `${user.mutual_followers_count} mutual followers` : user.is_private ? "Private account" : "Public profile"}</Text>
      </View>
      {action ? (
        <Pressable onPress={action} style={{ paddingHorizontal: 14, paddingVertical: 9, borderRadius: 999, backgroundColor: secondary ? colors.soft : colors.primary }}>
          <Text style={{ color: secondary ? colors.text : "white", fontWeight: "800" }}>{label}</Text>
        </Pressable>
      ) : null}
    </Pressable>
  );
}
