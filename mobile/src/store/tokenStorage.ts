import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

function webStorage() {
  return typeof globalThis.localStorage === "undefined" ? null : globalThis.localStorage;
}

export async function setTokenItem(key: string, value: string) {
  if (Platform.OS === "web") {
    webStorage()?.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

export async function getTokenItem(key: string) {
  if (Platform.OS === "web") {
    return webStorage()?.getItem(key) ?? null;
  }
  return SecureStore.getItemAsync(key);
}

export async function deleteTokenItem(key: string) {
  if (Platform.OS === "web") {
    webStorage()?.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}
