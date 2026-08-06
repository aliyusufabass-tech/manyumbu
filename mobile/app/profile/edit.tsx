import * as ImagePicker from "expo-image-picker";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Image, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { getMyProfile, removeProfileMedia, updateProfile, uploadProfileMedia } from "../../src/api/profile";
import type { Profile } from "../../src/types/profile";
import { ScreenState } from "../../src/components/UserList";
import { ensureMediaPermission } from "../../src/media/permissions";
import { useAuthStore } from "../../src/store/authStore";

const maxImageBytes = 5 * 1024 * 1024;
type EditProfileForm = Pick<Profile, "full_name" | "username" | "bio" | "website" | "location" | "account_type">;
type PickedImage = { kind: "profile_picture" | "cover_photo"; uri: string; name: string; type: string; size?: number };

export default function EditProfileScreen() {
  const client = useQueryClient();
  const authUser = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);
  const query = useQuery({ queryKey: ["profile", "me"], queryFn: getMyProfile });
  const [form, setForm] = useState<EditProfileForm>({ full_name: "", username: "", bio: "", website: "", location: "", account_type: "personal" });
  const [uploadProgress, setUploadProgress] = useState(0);
  const [imageError, setImageError] = useState("");
  const [pendingImage, setPendingImage] = useState<PickedImage | null>(null);
  useEffect(() => { if (query.data) { const p = query.data.data.profile; setForm({ full_name: p.full_name, username: p.username, bio: p.bio, website: p.website, location: p.location, account_type: p.account_type }); } }, [query.data]);
  const refreshProfileCaches = () => {
    client.invalidateQueries({ queryKey: ["profile"] });
    client.invalidateQueries({ queryKey: ["feed"] });
    client.invalidateQueries({ queryKey: ["comments"] });
    client.invalidateQueries({ queryKey: ["conversations"] });
    client.invalidateQueries({ queryKey: ["groups"] });
    client.invalidateQueries({ queryKey: ["profiles"] });
  };
  const mutation = useMutation({ mutationFn: () => updateProfile(form), onSuccess: (data) => { if (authUser) setUser({ ...authUser, full_name: data.data.profile.full_name, username: data.data.profile.username, email: data.data.profile.email ?? authUser.email }); refreshProfileCaches(); } });
  const upload = useMutation({ mutationFn: () => pendingImage ? uploadProfileMedia(pendingImage.kind, pendingImage, setUploadProgress) : Promise.reject(new Error("Choose a photo first.")), onSuccess: () => { setPendingImage(null); refreshProfileCaches(); } });
  const remove = useMutation({ mutationFn: removeProfileMedia, onSuccess: () => refreshProfileCaches() });

  async function chooseImage(kind: "profile_picture" | "cover_photo", source: "camera" | "gallery") {
    setImageError("");
    if (!(await ensureMediaPermission(source))) return;
    const options: ImagePicker.ImagePickerOptions = { mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.82, allowsEditing: true };
    const result = source === "camera" ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
    if (result.canceled) return;
    const asset = result.assets[0];
    const mime = asset.mimeType ?? "image/jpeg";
    if (!["image/jpeg", "image/png", "image/webp"].includes(mime)) { setImageError("Choose a JPEG, PNG, or WebP image."); return; }
    if (asset.fileSize && asset.fileSize > maxImageBytes) { setImageError("Image must be 5MB or smaller."); return; }
    setPendingImage({ kind, uri: asset.uri, name: asset.fileName ?? `${kind}.jpg`, type: mime, size: asset.fileSize });
  }

  if (query.isLoading) return <ScreenState text="Loading profile..." />;
  const profile = query.data?.data.profile;
  return (
    <ScrollView contentContainerStyle={{ padding: 24, paddingTop: 64, gap: 14 }} style={{ backgroundColor: "#FFFFFF" }}>
      <Text style={{ fontSize: 28, fontWeight: "800" }}>Edit profile</Text>
      {pendingImage ? <Image source={{ uri: pendingImage.uri }} style={{ width: "100%", height: pendingImage.kind === "cover_photo" ? 150 : 180, borderRadius: 8, backgroundColor: "#DDEBE5" }} resizeMode="cover" /> : profile?.profile_picture ? <Image source={{ uri: profile.profile_picture }} style={{ width: 96, height: 96, borderRadius: 48, backgroundColor: "#DDEBE5" }} /> : null}
      {Object.entries(form).map(([key, value]) => <TextInput key={key} placeholder={key.replaceAll("_", " ")} value={value} onChangeText={(text) => setForm((next) => ({ ...next, [key]: text }))} style={{ borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 14 }} />)}
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        <Pressable onPress={() => chooseImage("profile_picture", "gallery")} style={{ borderWidth: 1, borderColor: "#126C57", padding: 12, borderRadius: 8 }}><Text style={{ color: "#126C57", fontWeight: "800" }}>Choose avatar</Text></Pressable>
        <Pressable onPress={() => chooseImage("profile_picture", "camera")} style={{ borderWidth: 1, borderColor: "#126C57", padding: 12, borderRadius: 8 }}><Text style={{ color: "#126C57", fontWeight: "800" }}>Camera avatar</Text></Pressable>
        <Pressable onPress={() => chooseImage("cover_photo", "gallery")} style={{ borderWidth: 1, borderColor: "#126C57", padding: 12, borderRadius: 8 }}><Text style={{ color: "#126C57", fontWeight: "800" }}>Choose cover</Text></Pressable>
        <Pressable onPress={() => remove.mutate("profile_picture")} style={{ borderWidth: 1, borderColor: "#B42318", padding: 12, borderRadius: 8 }}><Text style={{ color: "#B42318", fontWeight: "800" }}>Remove avatar</Text></Pressable>
      </View>
      {pendingImage ? <Pressable disabled={upload.isPending} onPress={() => upload.mutate()} style={{ backgroundColor: "#126C57", padding: 14, borderRadius: 8, alignItems: "center" }}><Text style={{ color: "white", fontWeight: "800" }}>{upload.isPending ? `Uploading ${uploadProgress}%` : `Save ${pendingImage.kind === "profile_picture" ? "avatar" : "cover"}`}</Text></Pressable> : null}
      {imageError || upload.error ? <Text style={{ color: "#B42318" }}>{imageError || upload.error?.message}</Text> : null}
      {mutation.error ? <Text style={{ color: "#B42318" }}>{mutation.error.message}</Text> : null}
      {mutation.data ? <Text style={{ color: "#126C57" }}>{mutation.data.message}</Text> : null}
      <Pressable onPress={() => mutation.mutate()} disabled={mutation.isPending} style={{ backgroundColor: "#126C57", padding: 16, borderRadius: 8, alignItems: "center" }}><Text style={{ color: "white", fontWeight: "800" }}>{mutation.isPending ? "Saving..." : "Save changes"}</Text></Pressable>
    </ScrollView>
  );
}
