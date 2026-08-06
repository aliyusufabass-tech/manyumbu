import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { Image, Modal, Pressable, SafeAreaView, ScrollView, Text, TextInput, View } from "react-native";
import { createStory } from "../../src/api/phase4";
import { ensureMediaPermission } from "../../src/media/permissions";
import { AppHeader } from "../../src/components/AppHeader";
import { PrimaryButton } from "../../src/components/PrimaryButton";
import { colors } from "../../src/theme/theme";
import { validateStoryDraft } from "../../src/phase4/validation";

type StoryMedia = { uri: string; name: string; type: string; size?: number };
const audiences = [
  { value: "everyone", label: "Everyone", description: "Anyone who can view your profile" },
  { value: "followers", label: "Followers", description: "People who follow you" },
  { value: "close_friends", label: "Close friends", description: "Your close friends list" },
  { value: "selected", label: "Selected people", description: "Choose a smaller audience later" },
  { value: "hide_selected", label: "Hide from selected", description: "Exclude specific people later" },
];

function OptionButton({ icon, title, onPress }: { icon: keyof typeof Ionicons.glyphMap; title: string; onPress: () => void }) {
  return <Pressable onPress={onPress} style={({ pressed }) => ({ flex: 1, minHeight: 82, borderRadius: 16, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border, alignItems: "center", justifyContent: "center", gap: 8, opacity: pressed ? 0.86 : 1 })}><Ionicons name={icon} size={25} color={colors.primary} /><Text style={{ color: colors.text, fontWeight: "900" }}>{title}</Text></Pressable>;
}

export default function StoryComposer() {
  const client = useQueryClient();
  const [caption, setCaption] = useState("");
  const [audience, setAudience] = useState("everyone");
  const [media, setMedia] = useState<StoryMedia | undefined>();
  const [audienceOpen, setAudienceOpen] = useState(false);
  const [progress, setProgress] = useState(0);
  const selectedAudience = audiences.find((item) => item.value === audience) ?? audiences[0];
  const errors = useMemo(() => validateStoryDraft({ text: caption, media }), [caption, media]);
  const mutation = useMutation({ mutationFn: () => createStory({ caption, audience, background_style: media ? undefined : "mint", media }, setProgress), onSuccess: () => { client.invalidateQueries({ queryKey: ["stories"] }); client.invalidateQueries({ queryKey: ["profile"] }); router.replace("/(tabs)/home"); } });

  async function pick(source: "camera" | "gallery") {
    if (!(await ensureMediaPermission(source))) return;
    const result = source === "camera"
      ? await ImagePicker.launchCameraAsync({ mediaTypes: ImagePicker.MediaTypeOptions.All, quality: 0.82 })
      : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.All, quality: 0.82 });
    if (!result.canceled) {
      const asset = result.assets[0];
      setMedia({ uri: asset.uri, name: asset.fileName ?? `story-${Date.now()}`, type: asset.mimeType ?? "image/jpeg", size: asset.fileSize });
    }
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.soft }}>
      <AppHeader title="Create story" subtitle="Share a quick moment" showBack />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 90 }} keyboardShouldPersistTaps="handled">
        <View style={{ minHeight: 320, borderRadius: 22, overflow: "hidden", backgroundColor: media ? colors.text : colors.primaryDark, alignItems: "center", justifyContent: "center", padding: 22 }}>
          {media?.type.startsWith("image/") ? <Image source={{ uri: media.uri }} style={{ position: "absolute", width: "100%", height: "100%" }} resizeMode="cover" /> : null}
          {media && !media.type.startsWith("image/") ? <View style={{ alignItems: "center", gap: 10 }}><Ionicons name="play-circle" size={70} color="white" /><Text style={{ color: "white", fontWeight: "900" }}>Video story selected</Text></View> : null}
          {!media && !caption.trim() ? <View style={{ alignItems: "center", gap: 10 }}><Ionicons name="sparkles-outline" size={44} color="white" /><Text style={{ color: "white", fontSize: 22, fontWeight: "900", textAlign: "center" }}>Text story</Text></View> : null}
          {caption.trim() ? <Text style={{ color: "white", fontSize: media ? 22 : 28, fontWeight: "900", textAlign: "center", lineHeight: media ? 29 : 36, textShadowColor: "rgba(0,0,0,.35)", textShadowRadius: 8 }}>{caption}</Text> : null}
        </View>

        <View style={{ flexDirection: "row", gap: 10 }}>
          <OptionButton icon="camera-outline" title="Camera" onPress={() => pick("camera")} />
          <OptionButton icon="images-outline" title="Gallery" onPress={() => pick("gallery")} />
          <OptionButton icon="text-outline" title="Text" onPress={() => setMedia(undefined)} />
        </View>

        <View style={{ backgroundColor: colors.background, borderRadius: 18, borderWidth: 1, borderColor: colors.border, padding: 14, gap: 10 }}>
          <Text style={{ color: colors.text, fontWeight: "900" }}>Caption</Text>
          <TextInput placeholder="Write something for your story" placeholderTextColor={colors.muted} value={caption} onChangeText={setCaption} multiline style={{ minHeight: 96, color: colors.text, textAlignVertical: "top", fontSize: 16 }} />
        </View>

        <Pressable onPress={() => setAudienceOpen(true)} style={({ pressed }) => ({ backgroundColor: colors.background, borderRadius: 18, borderWidth: 1, borderColor: colors.border, padding: 16, flexDirection: "row", alignItems: "center", gap: 12, opacity: pressed ? 0.86 : 1 })}>
          <Ionicons name="people-outline" size={24} color={colors.primary} />
          <View style={{ flex: 1 }}><Text style={{ color: colors.text, fontWeight: "900" }}>{selectedAudience.label}</Text><Text style={{ color: colors.muted, marginTop: 3 }}>{selectedAudience.description}</Text></View>
          <Ionicons name="chevron-forward" size={20} color={colors.muted} />
        </Pressable>

        {media ? <Text style={{ color: colors.muted }}>Selected media: {media.type}</Text> : <Text style={{ color: colors.muted }}>Text story mode. Add media anytime from Camera or Gallery.</Text>}
        {errors.map((error) => <Text key={error} style={{ color: colors.error }}>{error}</Text>)}
        {mutation.isError ? <Text style={{ color: colors.error }}>{mutation.error.message}</Text> : null}
        {mutation.isPending ? <Text style={{ color: colors.primary, fontWeight: "900" }}>Publishing {progress}%</Text> : null}
        <PrimaryButton title="Publish story" loading={mutation.isPending} disabled={errors.length > 0 || mutation.isPending} onPress={() => mutation.mutate()} />
      </ScrollView>

      <Modal visible={audienceOpen} transparent animationType="slide" onRequestClose={() => setAudienceOpen(false)}>
        <Pressable onPress={() => setAudienceOpen(false)} style={{ flex: 1, backgroundColor: "rgba(17,24,39,.32)", justifyContent: "flex-end" }}>
          <Pressable style={{ backgroundColor: colors.background, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 18, gap: 8 }}>
            <Text style={{ color: colors.text, fontSize: 20, fontWeight: "900", marginBottom: 4 }}>Story audience</Text>
            {audiences.map((item) => <Pressable key={item.value} onPress={() => { setAudience(item.value); setAudienceOpen(false); }} style={{ flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 13 }}><Ionicons name={audience === item.value ? "radio-button-on" : "radio-button-off"} size={22} color={audience === item.value ? colors.primary : colors.muted} /><View style={{ flex: 1 }}><Text style={{ color: colors.text, fontWeight: "900" }}>{item.label}</Text><Text style={{ color: colors.muted, marginTop: 2 }}>{item.description}</Text></View></Pressable>)}
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}
