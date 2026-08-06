import { useEffect, useState } from "react";
import { SafeAreaView, Switch, Text, View } from "react-native";
import { AppHeader } from "../../src/components/AppHeader";
import { SettingsRow } from "../../src/components/SettingsRow";
import { getTokenItem, setTokenItem } from "../../src/store/tokenStorage";
import { colors } from "../../src/theme/theme";

type Prefs = { language: string; theme: string; data_saver: boolean };
const defaults: Prefs = { language: "English", theme: "System", data_saver: false };

export default function PreferencesScreen() {
  const [prefs, setPrefs] = useState(defaults);
  useEffect(() => { getTokenItem("manyumbu_preferences").then((raw) => raw && setPrefs({ ...defaults, ...JSON.parse(raw) })); }, []);
  const save = async (next: Prefs) => { setPrefs(next); await setTokenItem("manyumbu_preferences", JSON.stringify(next)); };
  return <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}><AppHeader title="Preferences" showBack /><View style={{ padding: 18 }}><SettingsRow icon="language-outline" title="Language" value={prefs.language} onPress={() => save({ ...prefs, language: prefs.language === "English" ? "Swahili" : "English" })} /><SettingsRow icon="moon-outline" title="Theme" value={prefs.theme} onPress={() => save({ ...prefs, theme: prefs.theme === "System" ? "Light" : prefs.theme === "Light" ? "Dark" : "System" })} /><View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 14 }}><Text style={{ color: colors.text, fontWeight: "800", fontSize: 16 }}>Data saver</Text><Switch value={prefs.data_saver} onValueChange={(value) => save({ ...prefs, data_saver: value })} /></View></View></SafeAreaView>;
}
