import { FlatList, Pressable, Text, View } from "react-native";
import type { CompactUser } from "../types/profile";

export function UserList({ users, emptyText, onPress }: { users: CompactUser[]; emptyText: string; onPress?: (user: CompactUser) => void }) {
  return (
    <FlatList
      data={users}
      keyExtractor={(item) => item.username}
      ListEmptyComponent={<Text style={{ color: "#52605B", padding: 20, textAlign: "center" }}>{emptyText}</Text>}
      renderItem={({ item }) => (
        <Pressable onPress={() => onPress?.(item)} style={{ paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: "#E6EEEA" }}>
          <Text style={{ fontWeight: "800", color: "#14231F" }}>{item.full_name}{item.is_verified ? " ?" : ""}</Text>
          <Text style={{ color: "#52605B" }}>@{item.username}{item.is_private ? " · private" : ""}</Text>
        </Pressable>
      )}
    />
  );
}

export function ScreenState({ text }: { text: string }) {
  return <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: 24 }}><Text style={{ color: "#52605B" }}>{text}</Text></View>;
}
