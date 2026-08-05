import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { FlatList, Pressable, Text, TextInput, View } from "react-native";
import { addGroupMembers, createGroupInvitation, decideJoinRequest, getGroup, groupAction, listGroupMembers, listJoinRequests } from "../../src/api/groups";
import { canModerateRole, parseMemberInput } from "../../src/groups/validation";

export default function GroupInfoScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const groupId = String(id);
  const [members, setMembers] = useState("");
  const [inviteToken, setInviteToken] = useState("");
  const client = useQueryClient();
  const group = useQuery({ queryKey: ["group", groupId], queryFn: () => getGroup(groupId) });
  const memberList = useQuery({ queryKey: ["group-members", groupId], queryFn: () => listGroupMembers(groupId) });
  const requests = useQuery({ queryKey: ["group-join-requests", groupId], queryFn: () => listJoinRequests(groupId), enabled: canModerateRole(group.data?.data.group.viewer_role) });
  const addMembers = useMutation({ mutationFn: () => addGroupMembers(groupId, parseMemberInput(members)), onSuccess: () => { setMembers(""); client.invalidateQueries({ queryKey: ["group-members", groupId] }); client.invalidateQueries({ queryKey: ["group", groupId] }); } });
  const invite = useMutation({ mutationFn: () => createGroupInvitation(groupId), onSuccess: (result) => setInviteToken(result.data.token) });
  const decide = useMutation({ mutationFn: ({ requestId, action }: { requestId: string; action: "approve" | "reject" }) => decideJoinRequest(groupId, requestId, action), onSuccess: () => requests.refetch() });
  const item = group.data?.data.group;
  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 48, paddingHorizontal: 18 }}><Pressable onPress={() => router.back()}><Text style={{ color: "#126C57", fontWeight: "800" }}>Back</Text></Pressable><Text style={{ fontSize: 26, fontWeight: "900", marginTop: 16 }}>{item?.name ?? "Group info"}</Text><Text style={{ color: "#4B5563", marginTop: 6 }}>{item?.description || "No description"}</Text><Text style={{ color: "#6B7280", marginTop: 6 }}>{item?.privacy} · {item?.viewer_role} · {item?.member_count} members</Text><View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 14 }}><Pressable onPress={() => invite.mutate()}><Text style={{ color: "#126C57", fontWeight: "800" }}>Create invite</Text></Pressable><Pressable onPress={() => groupAction(groupId, "leave").then(() => router.replace("/groups"))}><Text style={{ color: "#B91C1C", fontWeight: "800" }}>Leave</Text></Pressable></View>{inviteToken ? <Text selectable style={{ color: "#126C57", marginTop: 8 }}>Invite token: {inviteToken}</Text> : null}<TextInput value={members} onChangeText={setMembers} autoCapitalize="none" placeholder="Add usernames" style={{ borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12, marginTop: 14 }} /><Pressable onPress={() => addMembers.mutate()} style={{ backgroundColor: "#126C57", padding: 12, borderRadius: 8, marginTop: 8, alignItems: "center" }}><Text style={{ color: "white", fontWeight: "900" }}>Add members</Text></Pressable><Text style={{ fontWeight: "900", marginTop: 18 }}>Members</Text><FlatList data={memberList.data?.data.results ?? []} keyExtractor={(row) => row.user.username} renderItem={({ item: row }) => <View style={{ paddingVertical: 10, borderBottomWidth: 1, borderColor: "#E5E7EB" }}><Text style={{ fontWeight: "800" }}>{row.user.full_name}</Text><Text style={{ color: "#6B7280" }}>@{row.user.username} · {row.role}</Text></View>} />{canModerateRole(item?.viewer_role) ? <View style={{ marginTop: 12 }}><Text style={{ fontWeight: "900" }}>Join requests</Text>{(requests.data?.data.results ?? []).map((row) => <View key={row.id} style={{ paddingVertical: 10 }}><Text>{row.requester.full_name}</Text><View style={{ flexDirection: "row", gap: 12 }}><Pressable onPress={() => decide.mutate({ requestId: row.id, action: "approve" })}><Text style={{ color: "#126C57" }}>Approve</Text></Pressable><Pressable onPress={() => decide.mutate({ requestId: row.id, action: "reject" })}><Text style={{ color: "#B91C1C" }}>Reject</Text></Pressable></View></View>)}</View> : null}</View>;
}
