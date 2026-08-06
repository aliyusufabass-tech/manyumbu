import * as ImagePicker from "expo-image-picker";
import { ResizeMode, Video } from "expo-av";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { createReel } from "../../src/api/phase4";
import { ensureMediaPermission } from "../../src/media/permissions";
import { validateReelDraft } from "../../src/phase4/validation";

export default function ReelComposer() {
  const client = useQueryClient();
  const [caption, setCaption] = useState("");
  const [audience, setAudience] = useState("public");
  const [video, setVideo] = useState<{ uri: string; name: string; type: string; size?: number; duration?: number } | undefined>();
  const [progress, setProgress] = useState(0);
  const errors = useMemo(() => validateReelDraft({ caption, video }), [caption, video]);
  const mutation = useMutation({ mutationFn: (status: string) => createReel({ caption, audience, video: video!, status, duration: video?.duration }, setProgress), onSuccess: () => { client.invalidateQueries({ queryKey: ["reels"] }); client.invalidateQueries({ queryKey: ["user-reels"] }); client.invalidateQueries({ queryKey: ["profile"] }); router.replace("/reels"); } });
  async function pick(source: "camera" | "gallery") {
    if (!(await ensureMediaPermission(source))) return;
    const options: ImagePicker.ImagePickerOptions = { mediaTypes: ImagePicker.MediaTypeOptions.Videos, quality: 0.82 };
    const result = source === "camera" ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
    if (!result.canceled) {
      const a = result.assets[0];
      setVideo({ uri: a.uri, name: a.fileName ?? "reel.mp4", type: a.mimeType ?? "video/mp4", size: a.fileSize, duration: a.duration ? a.duration / 1000 : undefined });
    }
  }
  return <ScrollView style={{ backgroundColor: "#FFFFFF" }} contentContainerStyle={{ padding: 24, paddingTop: 64, gap: 14 }}><Text style={{ fontSize: 28, fontWeight: "800" }}>Create reel</Text><TextInput placeholder="Caption" value={caption} onChangeText={setCaption} multiline style={{ minHeight: 110, borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 14 }} /><View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>{["public", "followers", "close_friends", "selected", "only_me"].map((item) => <Pressable key={item} onPress={() => setAudience(item)} style={{ padding: 10, borderRadius: 8, backgroundColor: audience === item ? "#126C57" : "#EAF4EF" }}><Text style={{ color: audience === item ? "white" : "#14231F" }}>{item.replace("_", " ")}</Text></Pressable>)}</View><View style={{ flexDirection: "row", gap: 10, flexWrap: "wrap" }}><Pressable onPress={() => pick("gallery")} style={{ borderWidth: 1, borderColor: "#126C57", borderRadius: 8, padding: 14 }}><Text style={{ color: "#126C57", fontWeight: "800" }}>{video ? "Replace video" : "Choose video"}</Text></Pressable><Pressable onPress={() => pick("camera")} style={{ borderWidth: 1, borderColor: "#126C57", borderRadius: 8, padding: 14 }}><Text style={{ color: "#126C57", fontWeight: "800" }}>Record video</Text></Pressable></View>{video ? <Video source={{ uri: video.uri }} useNativeControls resizeMode={ResizeMode.CONTAIN} style={{ width: "100%", height: 360, borderRadius: 8, backgroundColor: "#101816" }} /> : null}{video ? <Text>{video.name}</Text> : null}{errors.map((e) => <Text key={e} style={{ color: "#B42318" }}>{e}</Text>)}{mutation.isPending ? <Text>Uploading {progress}%</Text> : null}<Pressable disabled={errors.length > 0 || mutation.isPending} onPress={() => mutation.mutate("published")} style={{ backgroundColor: "#126C57", borderRadius: 8, padding: 16, alignItems: "center", opacity: errors.length ? 0.5 : 1 }}><Text style={{ color: "white", fontWeight: "800" }}>Publish reel</Text></Pressable><Pressable disabled={!video || mutation.isPending} onPress={() => mutation.mutate("draft")}><Text style={{ color: "#126C57", fontWeight: "800", textAlign: "center" }}>Save draft</Text></Pressable></ScrollView>;
}
