import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router, useLocalSearchParams } from "expo-router";
import { useMemo, useState } from "react";
import { FlatList, Pressable, Text, TextInput, View } from "react-native";
import { addGroupMembers, createGroupInvitation, decideJoinRequest, getGroup, groupAction, listGroupMembers, listJoinRequests, removeGroupMember, updateGroupMemberRole } from "../../src/api/groups";
import { searchProfiles } from "../../src/api/profile";
import { canModerateRole, parseMemberInput } from "../../src/groups/validation";
import type { GroupMember, GroupRole } from "../../src/types/groups";
import type { CompactUser } from "../../src/types/profile";

function RoleBadge({ role }: { role: GroupRole }) {
  const backgroundColor = role === "owner" ? "#111827" : role === "admin" ? "#126C57" : role === "moderator" ? "#92400E" : "#E5E7EB";
  const color = role === "member" ? "#374151" : "#FFFFFF";
  return <Text style={{ backgroundColor, color, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3, overflow: "hidden", fontSize: 12, fontWeight: "900" }}>{role}</Text>;
}

function SearchRow({ user, selected, onToggle }: { user: CompactUser; selected: boolean; onToggle: () => void }) {
  return <Pressable onPress={onToggle} style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 10, borderBottomWidth: 1, borderColor: "#E5E7EB" }}><View><Text style={{ fontWeight: "900" }}>{user.full_name}</Text><Text style={{ color: "#6B7280" }}>@{user.username}</Text></View><Text style={{ color: selected ? "#B91C1C" : "#126C57", fontWeight: "900" }}>{selected ? "Selected" : "Add"}</Text></Pressable>;
}

function MemberRow({ row, canManage, onRemove, onRole }: { row: GroupMember; canManage: boolean; onRemove: () => void; onRole: (role: "admin" | "moderator" | "member") => void }) {
  const canChange = canManage && row.role !== "owner";
  return <View style={{ paddingVertical: 10, borderBottomWidth: 1, borderColor: "#E5E7EB", gap: 8 }}><View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}><View><Text style={{ fontWeight: "900" }}>{row.user.full_name}</Text><Text style={{ color: "#6B7280" }}>@{row.user.username}</Text></View><RoleBadge role={row.role} /></View>{canChange ? <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}><Pressable onPress={() => onRole(row.role === "admin" ? "member" : "admin")}><Text style={{ color: "#126C57", fontWeight: "800" }}>{row.role === "admin" ? "Demote" : "Promote admin"}</Text></Pressable><Pressable onPress={() => onRole(row.role === "moderator" ? "member" : "moderator")}><Text style={{ color: "#126C57", fontWeight: "800" }}>{row.role === "moderator" ? "Demote mod" : "Make mod"}</Text></Pressable><Pressable onPress={onRemove}><Text style={{ color: "#B91C1C", fontWeight: "800" }}>Remove</Text></Pressable></View> : null}</View>;
}

export default function GroupInfoScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const groupId = String(id);
  const [members, setMembers] = useState("");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [inviteToken, setInviteToken] = useState("");
  const client = useQueryClient();
  const group = useQuery({ queryKey: ["group", groupId], queryFn: () => getGroup(groupId) });
  const memberList = useQuery({ queryKey: ["group-members", groupId], queryFn: () => listGroupMembers(groupId) });
  const item = group.data?.data.group;
  const canManage = canModerateRole(item?.viewer_role);
  const requests = useQuery({ queryKey: ["group-join-requests", groupId], queryFn: () => listJoinRequests(groupId), enabled: canManage });
  const users = useQuery({ queryKey: ["profiles", "group-member-search", q], queryFn: () => searchProfiles(q), enabled: canManage && q.trim().length > 0 });
  const currentUsernames = useMemo(() => new Set((memberList.data?.data.results ?? []).map((row) => row.user.username)), [memberList.data]);
  const pendingMembers = useMemo(() => Array.from(new Set([...parseMemberInput(members), ...selected])).filter((username) => !currentUsernames.has(username)), [members, selected, currentUsernames]);
  const invalidateMembers = () => { client.invalidateQueries({ queryKey: ["group-members", groupId] }); client.invalidateQueries({ queryKey: ["group", groupId] }); client.invalidateQueries({ queryKey: ["groups"] }); };
  const addMembers = useMutation({ mutationFn: () => addGroupMembers(groupId, pendingMembers), onSuccess: () => { setMembers(""); setSelected([]); invalidateMembers(); } });
  const remove = useMutation({ mutationFn: (username: string) => removeGroupMember(groupId, username), onSuccess: invalidateMembers });
  const role = useMutation({ mutationFn: ({ username, role }: { username: string; role: "admin" | "moderator" | "member" }) => updateGroupMemberRole(groupId, username, role), onSuccess: invalidateMembers });
  const invite = useMutation({ mutationFn: () => createGroupInvitation(groupId), onSuccess: (result) => setInviteToken(result.data.token) });
  const decide = useMutation({ mutationFn: ({ requestId, action }: { requestId: string; action: "approve" | "reject" }) => decideJoinRequest(groupId, requestId, action), onSuccess: () => { requests.refetch(); invalidateMembers(); } });

  return <View style={{ flex: 1, backgroundColor: "#FFFFFF", paddingTop: 48, paddingHorizontal: 18 }}><Pressable onPress={() => router.back()}><Text style={{ color: "#126C57", fontWeight: "800" }}>Back</Text></Pressable><Text style={{ fontSize: 26, fontWeight: "900", marginTop: 16 }}>{item?.name ?? "Group info"}</Text><Text style={{ color: "#4B5563", marginTop: 6 }}>{item?.description || "No description"}</Text><Text style={{ color: "#6B7280", marginTop: 6 }}>{item?.privacy} · {item?.viewer_role} · {item?.member_count} members</Text><View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 14 }}><Pressable onPress={() => invite.mutate()} disabled={!canManage}><Text style={{ color: canManage ? "#126C57" : "#9CA3AF", fontWeight: "800" }}>Create invite</Text></Pressable><Pressable onPress={() => groupAction(groupId, "leave").then(() => router.replace("/groups"))}><Text style={{ color: "#B91C1C", fontWeight: "800" }}>Leave</Text></Pressable></View>{inviteToken ? <Text selectable style={{ color: "#126C57", marginTop: 8 }}>Invite token: {inviteToken}</Text> : null}{canManage ? <View style={{ marginTop: 14, gap: 8 }}><TextInput value={q} onChangeText={setQ} autoCapitalize="none" placeholder="Search users to add" style={{ borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12 }} />{(users.data?.data.results ?? []).filter((user) => !currentUsernames.has(user.username)).map((user) => <SearchRow key={user.username} user={user} selected={selected.includes(user.username)} onToggle={() => setSelected((items) => items.includes(user.username) ? items.filter((name) => name !== user.username) : [...items, user.username])} />)}<TextInput value={members} onChangeText={setMembers} autoCapitalize="none" placeholder="Or paste usernames separated by commas" style={{ borderWidth: 1, borderColor: "#D1D5DB", borderRadius: 8, padding: 12 }} /><Pressable disabled={!pendingMembers.length || addMembers.isPending} onPress={() => addMembers.mutate()} style={{ backgroundColor: pendingMembers.length ? "#126C57" : "#9CA3AF", padding: 12, borderRadius: 8, alignItems: "center" }}><Text style={{ color: "white", fontWeight: "900" }}>{addMembers.isPending ? "Adding..." : `Add ${pendingMembers.length || ""} members`}</Text></Pressable>{addMembers.isError ? <Text style={{ color: "#B91C1C" }}>{addMembers.error.message}</Text> : null}</View> : null}<Text style={{ fontWeight: "900", marginTop: 18 }}>Members</Text><FlatList data={memberList.data?.data.results ?? []} keyExtractor={(row) => row.user.username} renderItem={({ item: row }) => <MemberRow row={row} canManage={canManage} onRemove={() => remove.mutate(row.user.username)} onRole={(nextRole) => role.mutate({ username: row.user.username, role: nextRole })} />} ListFooterComponent={canManage ? <View style={{ marginTop: 12 }}><Text style={{ fontWeight: "900" }}>Join requests</Text>{(requests.data?.data.results ?? []).map((row) => <View key={row.id} style={{ paddingVertical: 10 }}><Text>{row.requester.full_name}</Text><View style={{ flexDirection: "row", gap: 12 }}><Pressable onPress={() => decide.mutate({ requestId: row.id, action: "approve" })}><Text style={{ color: "#126C57" }}>Approve</Text></Pressable><Pressable onPress={() => decide.mutate({ requestId: row.id, action: "reject" })}><Text style={{ color: "#B91C1C" }}>Reject</Text></Pressable></View></View>)}</View> : null} /></View>;
}
