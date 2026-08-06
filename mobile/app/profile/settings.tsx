import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import { SafeAreaView, ScrollView, Text, View } from "react-native";
import { AppHeader } from "../../src/components/AppHeader";
import { ConfirmationModal } from "../../src/components/ConfirmationModal";
import { SettingsRow } from "../../src/components/SettingsRow";
import { colors } from "../../src/theme/theme";
import { useAuthStore } from "../../src/store/authStore";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <View style={{ backgroundColor: colors.background, borderRadius: 18, paddingHorizontal: 16, borderWidth: 1, borderColor: colors.border }}><Text style={{ color: colors.muted, fontWeight: "900", marginTop: 16, marginBottom: 2, textTransform: "uppercase", fontSize: 12 }}>{title}</Text>{children}</View>;
}

export default function AccountSettingsScreen() {
  const [logoutVisible, setLogoutVisible] = useState(false);
  const [deleteVisible, setDeleteVisible] = useState(false);
  const signOut = useAuthStore((state) => state.signOut);
  const logout = async () => { await signOut(); setLogoutVisible(false); router.replace("/login"); };
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.soft }}>
      <AppHeader title="Settings" showBack />
      <ScrollView contentContainerStyle={{ padding: 14, gap: 14, paddingBottom: 90 }}>
        <Section title="Account"><SettingsRow icon="person-outline" title="Edit profile" subtitle="Name, bio, photos, and personal details" onPress={() => router.push("/profile/edit")} /><SettingsRow icon="key-outline" title="Change password" subtitle="Update your sign-in password" /><SettingsRow icon="mail-outline" title="Email and phone" subtitle="Manage contact information" /><SettingsRow icon="shield-checkmark-outline" title="Account status" subtitle="Review restrictions and account health" onPress={() => router.push("/moderation/appeals")} /></Section>
        <Section title="Privacy"><SettingsRow icon="lock-closed-outline" title="Private account" subtitle="Control who can view your content" onPress={() => router.push("/profile/privacy")} /><SettingsRow icon="ban-outline" title="Blocked users" onPress={() => router.push("/relationships/blocked")} /><SettingsRow icon="chatbubble-outline" title="Message permissions" onPress={() => router.push("/chats/requests")} /><SettingsRow icon="people-outline" title="Story privacy" onPress={() => router.push("/relationships/close-friends")} /></Section>
        <Section title="Notifications"><SettingsRow icon="chatbubbles-outline" title="Message notifications" /><SettingsRow icon="person-add-outline" title="Follow notifications" /><SettingsRow icon="heart-outline" title="Post notifications" /><SettingsRow icon="people-circle-outline" title="Group notifications" onPress={() => router.push("/groups")} /></Section>
        <Section title="Preferences"><SettingsRow icon="language-outline" title="Language" value="English" /><SettingsRow icon="moon-outline" title="Theme" value="System" /><SettingsRow icon="cellular-outline" title="Data saver" value="Off" /></Section>
        <Section title="Support"><SettingsRow icon="help-circle-outline" title="Help centre" /><SettingsRow icon="alert-circle-outline" title="Report a problem" /><SettingsRow icon="document-text-outline" title="Terms of service" /><SettingsRow icon="shield-outline" title="Privacy policy" /></Section>
        <Section title="Account actions"><SettingsRow icon="log-out-outline" title="Logout" danger onPress={() => setLogoutVisible(true)} /><SettingsRow icon="trash-outline" title="Delete account" subtitle="Permanently remove your account" danger onPress={() => setDeleteVisible(true)} /></Section>
      </ScrollView>
      <ConfirmationModal visible={logoutVisible} title="Log out?" message="You can sign back in anytime with your username, email, or phone." confirmLabel="Logout" onCancel={() => setLogoutVisible(false)} onConfirm={logout} />
      <ConfirmationModal visible={deleteVisible} title="Delete account?" message="This is a destructive action. Account deletion support should be confirmed before continuing." confirmLabel="Delete" danger onCancel={() => setDeleteVisible(false)} onConfirm={() => setDeleteVisible(false)} />
    </SafeAreaView>
  );
}