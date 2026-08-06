import * as ImagePicker from "expo-image-picker";
import { Alert, Linking } from "react-native";

export async function ensureMediaPermission(source: "camera" | "gallery") {
  const request = source === "camera" ? ImagePicker.requestCameraPermissionsAsync : ImagePicker.requestMediaLibraryPermissionsAsync;
  const permission = await request();
  if (permission.granted) return true;
  Alert.alert(
    source === "camera" ? "Camera permission needed" : "Photo library permission needed",
    source === "camera"
      ? "Allow camera access in device Settings to capture posts, stories, reels, and profile photos."
      : "Allow photo and video access in device Settings to choose uploads for Manyumbu.",
    [
      { text: "Not now", style: "cancel" },
      { text: "Open Settings", onPress: () => Linking.openSettings() },
    ],
  );
  return false;
}
