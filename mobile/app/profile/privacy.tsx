import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pressable, Switch, Text, View } from "react-native";
import { getPrivacy, updatePrivacy } from "../../src/api/profile";
import { ScreenState } from "../../src/components/UserList";

export default function PrivacyScreen() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["privacy"], queryFn: getPrivacy });
  const mutation = useMutation({ mutationFn: updatePrivacy, onSuccess: () => client.invalidateQueries({ queryKey: ["privacy"] }) });
  if (query.isLoading) return <ScreenState text="Loading privacy settings..." />;
  if (!query.data) return <ScreenState text="Privacy settings could not be loaded." />;
  const p = query.data.data.privacy;
  const toggle = (key: keyof typeof p) => mutation.mutate({ [key]: !p[key] });
  return (
    <View style={{ flex: 1, backgroundColor: "#FFFFFF", padding: 24, paddingTop: 64, gap: 18 }}>
      <Text style={{ fontSize: 28, fontWeight: "800" }}>Privacy</Text>
      {(["show_in_suggestions", "phone_discoverable", "profile_details_public", "online_status_visible"] as const).map((key) => <View key={key} style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}><Text>{key.replaceAll("_", " ")}</Text><Switch value={Boolean(p[key])} onValueChange={() => toggle(key)} /></View>)}
      <Pressable onPress={() => mutation.mutate({ dob_visibility: p.dob_visibility === "hidden" ? "month_day" : p.dob_visibility === "month_day" ? "full" : "hidden" })} style={{ borderWidth: 1, borderColor: "#CED9D4", padding: 14, borderRadius: 8 }}><Text>Date of birth visibility: {p.dob_visibility}</Text></Pressable>
    </View>
  );
}
