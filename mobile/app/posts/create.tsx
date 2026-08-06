import * as ImagePicker from "expo-image-picker";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { Image, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { createPost } from "../../src/api/posts";
import { ensureMediaPermission } from "../../src/media/permissions";
import { validateComposerDraft } from "../../src/posts/composerValidation";

const audiences = ["public", "followers", "close_friends", "selected", "only_me"];
type Picked = { uri: string; name: string; type: string; size?: number };

export default function CreatePostScreen() {
  const client = useQueryClient();
  const [caption, setCaption] = useState("");
  const [location, setLocation] = useState("");
  const [audience, setAudience] = useState("public");
  const [commentsEnabled, setCommentsEnabled] = useState(true);
  const [media, setMedia] = useState<Picked[]>([]);
  const [progress, setProgress] = useState(0);
  const errors = useMemo(() => validateComposerDraft({ caption, media, audience, commentsEnabled }), [caption, media, audience, commentsEnabled]);
  const mutation = useMutation({
    mutationFn: (status: "draft" | "published") => createPost({ caption, location_name: location, audience, comments_enabled: commentsEnabled, media, status }, setProgress),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["feed"] });
      client.invalidateQueries({ queryKey: ["user-posts"] });
      client.invalidateQueries({ queryKey: ["profile"] });
      router.replace("/feed");
    },
  });

  async function pick(kind: "image" | "video", source: "camera" | "gallery") {
    if (!(await ensureMediaPermission(source))) return;
    const options: ImagePicker.ImagePickerOptions = {
      mediaTypes: kind === "image" ? ImagePicker.MediaTypeOptions.Images : ImagePicker.MediaTypeOptions.Videos,
      allowsMultipleSelection: source === "gallery" && kind === "image",
      quality: 0.82,
    };
    const result = source === "camera" ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
    if (!result.canceled) {
      setMedia(result.assets.map((asset) => ({
        uri: asset.uri,
        name: asset.fileName ?? `post-${Date.now()}`,
        type: asset.mimeType ?? (kind === "image" ? "image/jpeg" : "video/mp4"),
        size: asset.fileSize,
      })));
    }
  }

  return (
    <ScrollView style={{ backgroundColor: "#FFFFFF" }} contentContainerStyle={{ padding: 24, paddingTop: 64, gap: 14 }}>
      <Text style={{ fontSize: 28, fontWeight: "800" }}>Create post</Text>
      <TextInput placeholder="Write a caption" multiline value={caption} onChangeText={setCaption} style={{ minHeight: 120, borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 14, textAlignVertical: "top" }} />
      <TextInput placeholder="Location" value={location} onChangeText={setLocation} style={{ borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 14 }} />
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {audiences.map((item) => (
          <Pressable key={item} onPress={() => setAudience(item)} style={{ padding: 10, borderRadius: 8, backgroundColor: audience === item ? "#126C57" : "#EAF4EF" }}>
            <Text style={{ color: audience === item ? "white" : "#14231F" }}>{item.replace("_", " ")}</Text>
          </Pressable>
        ))}
      </View>
      <Pressable onPress={() => setCommentsEnabled((value) => !value)}>
        <Text style={{ color: "#126C57", fontWeight: "800" }}>{commentsEnabled ? "Comments enabled" : "Comments disabled"}</Text>
      </Pressable>
      <View style={{ flexDirection: "row", gap: 10, flexWrap: "wrap" }}>
        <Pressable onPress={() => pick("image", "gallery")} style={{ borderWidth: 1, borderColor: "#126C57", padding: 12, borderRadius: 8 }}><Text style={{ color: "#126C57", fontWeight: "800" }}>Pick images</Text></Pressable>
        <Pressable onPress={() => pick("video", "gallery")} style={{ borderWidth: 1, borderColor: "#126C57", padding: 12, borderRadius: 8 }}><Text style={{ color: "#126C57", fontWeight: "800" }}>Pick video</Text></Pressable>
        <Pressable onPress={() => pick("image", "camera")} style={{ borderWidth: 1, borderColor: "#126C57", padding: 12, borderRadius: 8 }}><Text style={{ color: "#126C57", fontWeight: "800" }}>Camera</Text></Pressable>
      </View>
      {media.map((item, index) => (
        <View key={item.uri} style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
          <Image source={{ uri: item.uri }} style={{ width: 56, height: 56, borderRadius: 8, backgroundColor: "#DDEBE5" }} />
          <Text style={{ flex: 1 }}>Media {index + 1}</Text>
          <Pressable onPress={() => setMedia((items) => items.filter((_, i) => i !== index))}><Text style={{ color: "#B42318" }}>Remove</Text></Pressable>
        </View>
      ))}
      {errors.map((error) => <Text key={error} style={{ color: "#B42318" }}>{error}</Text>)}
      {mutation.error ? <Text style={{ color: "#B42318" }}>{mutation.error.message}</Text> : null}
      {mutation.isPending ? <Text>Uploading {progress}%</Text> : null}
      <Pressable disabled={errors.length > 0 || mutation.isPending} onPress={() => mutation.mutate("published")} style={{ backgroundColor: "#126C57", padding: 16, borderRadius: 8, alignItems: "center", opacity: errors.length ? 0.5 : 1 }}>
        <Text style={{ color: "white", fontWeight: "800" }}>Publish</Text>
      </Pressable>
      <Pressable disabled={mutation.isPending} onPress={() => mutation.mutate("draft")} style={{ padding: 14, alignItems: "center" }}>
        <Text style={{ color: "#126C57", fontWeight: "800" }}>Save draft</Text>
      </Pressable>
    </ScrollView>
  );
}
