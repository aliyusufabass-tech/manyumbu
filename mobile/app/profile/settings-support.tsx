import { useLocalSearchParams } from "expo-router";
import { Linking, SafeAreaView, Text, View } from "react-native";
import { AppHeader } from "../../src/components/AppHeader";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { colors } from "../../src/theme/theme";

const copy: Record<string, { title: string; body: string; action?: string }> = {
  help: { title: "Help centre", body: "For help with uploads, account access, messaging, groups, stories, or reels, contact Manyumbu support with your username and a short description of the issue.", action: "mailto:support@manyumbu.app?subject=Manyumbu%20Help" },
  report: { title: "Report a problem", body: "Send a report when something is broken or unsafe. Include what happened, the screen name, and any media or account involved.", action: "mailto:support@manyumbu.app?subject=Manyumbu%20Problem%20Report" },
  terms: { title: "Terms of service", body: "Use Manyumbu lawfully, respect other people, and do not upload content you do not have permission to share. Accounts that abuse the service may be restricted or removed." },
  privacy: { title: "Privacy policy", body: "Manyumbu uses your account details, content, device, and safety signals to run the app, protect users, and provide messaging, media, groups, calls, and recommendations." },
};

export default function SupportScreen() { const { topic = "help" } = useLocalSearchParams<{ topic?: string }>(); const page = copy[topic] ?? copy.help; return <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}><AppHeader title={page.title} showBack /><View style={{ padding: 18, gap: 14 }}><Text style={{ color: colors.text, lineHeight: 22 }}>{page.body}</Text>{page.action ? <PrimaryButton title="Contact support" onPress={() => Linking.openURL(page.action!)} /> : null}</View></SafeAreaView>; }
