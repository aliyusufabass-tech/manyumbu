import * as ImagePicker from "expo-image-picker";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { createStory } from "../../src/api/phase4";
import { validateStoryDraft } from "../../src/phase4/validation";

export default function StoryComposer() {
  const client = useQueryClient();
  const [caption, setCaption] = useState("");
  const [audience, setAudience] = useState("everyone");
  const [media, setMedia] = useState<{ uri: string; name: string; type: string; size?: number } | undefined>();
  const [progress, setProgress] = useState(0);
  const errors = useMemo(() => validateStoryDraft({ text: caption, media }), [caption, media]);
  const mutation = useMutation({ mutationFn: () => createStory({ caption, audience, background_style: "mint", media }, setProgress), onSuccess: () => { client.invalidateQueries({ queryKey: ["stories"] }); router.replace("/feed"); } });
  async function pick() { const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.All, quality: 0.82 }); if (!result.canceled) { const a = result.assets[0]; setMedia({ uri: a.uri, name: a.fileName ?? "story", type: a.mimeType ?? "image/jpeg", size: a.fileSize }); } }
  return <ScrollView style={{ backgroundColor: "#FFFFFF" }} contentContainerStyle={{ padding: 24, paddingTop: 64, gap: 14 }}><Text style={{ fontSize: 28, fontWeight: "800" }}>Create story</Text><TextInput placeholder="Text overlay or caption" value={caption} onChangeText={setCaption} multiline style={{ minHeight: 130, borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 14 }} /><View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>{["everyone", "followers", "close_friends", "selected", "hide_selected"].map((item) => <Pressable key={item} onPress={() => setAudience(item)} style={{ padding: 10, borderRadius: 8, backgroundColor: audience === item ? "#126C57" : "#EAF4EF" }}><Text style={{ color: audience === item ? "white" : "#14231F" }}>{item.replace("_", " ")}</Text></Pressable>)}</View><Pressable onPress={pick} style={{ borderWidth: 1, borderColor: "#126C57", borderRadius: 8, padding: 14 }}><Text style={{ color: "#126C57", fontWeight: "800" }}>{media ? "Replace media" : "Choose photo or video"}</Text></Pressable>{media ? <Text>Selected {media.type}</Text> : null}{errors.map((e) => <Text key={e} style={{ color: "#B42318" }}>{e}</Text>)}{mutation.isPending ? <Text>Uploading {progress}%</Text> : null}<Pressable disabled={errors.length > 0 || mutation.isPending} onPress={() => mutation.mutate()} style={{ backgroundColor: "#126C57", borderRadius: 8, padding: 16, alignItems: "center", opacity: errors.length ? 0.5 : 1 }}><Text style={{ color: "white", fontWeight: "800" }}>Publish story</Text></Pressable></ScrollView>;
}
