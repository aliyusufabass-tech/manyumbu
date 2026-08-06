import { useQuery } from "@tanstack/react-query";
import { SafeAreaView, Text, View } from "react-native";
import { api } from "../../src/api/client";
import { AppHeader } from "../../src/components/AppHeader";
import { colors } from "../../src/theme/theme";
import { getTokenItem } from "../../src/store/tokenStorage";

async function loadStatus() { const token = await getTokenItem("manyumbu_access"); const headers = token ? { Authorization: `Bearer ${token}` } : {}; const [restrictions, deletion] = await Promise.all([api.get("/moderation/restrictions/", { headers }), api.get("/account-deletion/", { headers })]); return { restrictions: restrictions.data.data.results ?? [], deletion: deletion.data.data.deletion_request }; }
export default function AccountStatusScreen() { const query = useQuery({ queryKey: ["account-status"], queryFn: loadStatus }); const count = query.data?.restrictions.length ?? 0; return <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}><AppHeader title="Account status" showBack /><View style={{ padding: 18, gap: 12 }}><Text style={{ fontSize: 24, fontWeight: "900", color: colors.text }}>{count === 0 ? "No active restrictions" : `${count} active restriction${count === 1 ? "" : "s"}`}</Text><Text style={{ color: colors.muted }}>Security alerts stay enabled to protect your account.</Text>{query.data?.deletion ? <Text style={{ color: colors.error }}>Deletion requested. Grace period ends {new Date(query.data.deletion.grace_period_ends_at).toLocaleDateString()}.</Text> : null}</View></SafeAreaView>; }
