import * as ImagePicker from "expo-image-picker";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { getMyProfile, removeProfileMedia, updateProfile, uploadProfileMedia } from "../../src/api/profile";
import type { Profile } from "../../src/types/profile";
import { ScreenState } from "../../src/components/UserList";

const maxImageBytes = 5 * 1024 * 1024;
type EditProfileForm = Pick<Profile, "full_name" | "username" | "bio" | "website" | "location" | "account_type">;

export default function EditProfileScreen() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["profile", "me"], queryFn: getMyProfile });
  const [form, setForm] = useState<EditProfileForm>({ full_name: "", username: "", bio: "", website: "", location: "", account_type: "personal" });
  const [uploadProgress, setUploadProgress] = useState(0);
  const [imageError, setImageError] = useState("");
  useEffect(() => { if (query.data) { const p = query.data.data.profile; setForm({ full_name: p.full_name, username: p.username, bio: p.bio, website: p.website, location: p.location, account_type: p.account_type }); } }, [query.data]);
  const mutation = useMutation({ mutationFn: () => updateProfile(form), onSuccess: () => client.invalidateQueries({ queryKey: ["profile"] }) });
  const upload = useMutation({ mutationFn: (kind: "profile_picture" | "cover_photo") => pickAndUpload(kind), onSuccess: () => client.invalidateQueries({ queryKey: ["profile"] }) });
  const remove = useMutation({ mutationFn: removeProfileMedia, onSuccess: () => client.invalidateQueries({ queryKey: ["profile"] }) });

  async function pickAndUpload(kind: "profile_picture" | "cover_photo") {
    setImageError("");
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.82, allowsEditing: true });
    if (result.canceled) return query.data!;
    const asset = result.assets[0];
    const mime = asset.mimeType ?? "image/jpeg";
    if (!["image/jpeg", "image/png", "image/webp"].includes(mime)) throw new Error("Choose a JPEG, PNG, or WebP image.");
    if (asset.fileSize && asset.fileSize > maxImageBytes) throw new Error("Image must be 5MB or smaller.");
    const name = asset.fileName ?? `${kind}.jpg`;
    return uploadProfileMedia(kind, { uri: asset.uri, name, type: mime }, setUploadProgress);
  }

  if (query.isLoading) return <ScreenState text="Loading profile..." />;
  return (
    <ScrollView contentContainerStyle={{ padding: 24, paddingTop: 64, gap: 14 }} style={{ backgroundColor: "#FFFFFF" }}>
      <Text style={{ fontSize: 28, fontWeight: "800" }}>Edit profile</Text>
      {Object.entries(form).map(([key, value]) => <TextInput key={key} placeholder={key.replaceAll("_", " ")} value={value} onChangeText={(text) => setForm((next) => ({ ...next, [key]: text }))} style={{ borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 14 }} />)}
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        <Pressable onPress={() => upload.mutate("profile_picture")} style={{ borderWidth: 1, borderColor: "#126C57", padding: 12, borderRadius: 8 }}><Text style={{ color: "#126C57", fontWeight: "800" }}>Upload avatar</Text></Pressable>
        <Pressable onPress={() => upload.mutate("cover_photo")} style={{ borderWidth: 1, borderColor: "#126C57", padding: 12, borderRadius: 8 }}><Text style={{ color: "#126C57", fontWeight: "800" }}>Upload cover</Text></Pressable>
        <Pressable onPress={() => remove.mutate("profile_picture")} style={{ borderWidth: 1, borderColor: "#B42318", padding: 12, borderRadius: 8 }}><Text style={{ color: "#B42318", fontWeight: "800" }}>Remove avatar</Text></Pressable>
      </View>
      {upload.isPending ? <Text style={{ color: "#52605B" }}>Uploading {uploadProgress}%</Text> : null}
      {imageError || upload.error ? <Text style={{ color: "#B42318" }}>{imageError || upload.error?.message}</Text> : null}
      {mutation.error ? <Text style={{ color: "#B42318" }}>{mutation.error.message}</Text> : null}
      {mutation.data ? <Text style={{ color: "#126C57" }}>{mutation.data.message}</Text> : null}
      <Pressable onPress={() => mutation.mutate()} disabled={mutation.isPending} style={{ backgroundColor: "#126C57", padding: 16, borderRadius: 8, alignItems: "center" }}><Text style={{ color: "white", fontWeight: "800" }}>{mutation.isPending ? "Saving..." : "Save changes"}</Text></Pressable>
    </ScrollView>
  );
}

