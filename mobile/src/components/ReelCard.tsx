import { Ionicons } from "@expo/vector-icons";
import { Pressable, Share, Text, View, useWindowDimensions } from "react-native";
import type { Reel } from "../types/phase4";
import { Avatar } from "./Avatar";

export function ReelCard({ reel, onLike, onSave }: { reel: Reel; onLike?: () => void; onSave?: () => void }) {
  const { height } = useWindowDimensions();
  return (
    <View style={{ height: Math.max(620, height - 70), backgroundColor: "#101816", padding: 20, justifyContent: "flex-end" }}>
      <View style={{ position: "absolute", inset: 0, alignItems: "center", justifyContent: "center", backgroundColor: "#101816" }}>
        <Ionicons name={reel.processing_status === "ready" ? "play-circle" : "hourglass-outline"} size={78} color="white" />
        <Text style={{ color: "rgba(255,255,255,.82)", marginTop: 10, fontWeight: "800" }}>{reel.processing_status === "ready" ? "Tap to play" : "Preparing video"}</Text>
      </View>
      <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 16 }}>
        <View style={{ flex: 1, gap: 10 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <Avatar uri={reel.author.profile_picture} name={reel.author.full_name || reel.author.username} size={42} />
            <View style={{ flex: 1 }}>
              <Text style={{ color: "white", fontWeight: "900", fontSize: 17 }}>@{reel.author.username}</Text>
              {reel.author.is_verified ? <Text style={{ color: "rgba(255,255,255,.78)", fontSize: 12 }}>Verified creator</Text> : null}
            </View>
          </View>
          {reel.caption ? <Text style={{ color: "white", lineHeight: 22, fontSize: 15 }}>{reel.caption}</Text> : null}
          <Text style={{ color: "rgba(255,255,255,.78)", fontWeight: "800" }}>{reel.like_count} likes  -  {reel.comment_count} comments  -  {reel.view_count} views</Text>
        </View>
        <View style={{ width: 58, alignItems: "center", gap: 18 }}>
          <Pressable onPress={onLike} style={{ alignItems: "center", gap: 4 }}><Ionicons name={reel.viewer_has_liked ? "heart" : "heart-outline"} size={31} color={reel.viewer_has_liked ? "#FF6B6B" : "white"} /><Text style={{ color: "white", fontWeight: "900", fontSize: 12 }}>{reel.like_count}</Text></Pressable>
          <Pressable style={{ alignItems: "center", gap: 4 }}><Ionicons name="chatbubble-outline" size={29} color="white" /><Text style={{ color: "white", fontWeight: "900", fontSize: 12 }}>{reel.comment_count}</Text></Pressable>
          <Pressable onPress={() => Share.share({ message: `manyumbu://reel/${reel.id}` })} style={{ alignItems: "center", gap: 4 }}><Ionicons name="paper-plane-outline" size={29} color="white" /><Text style={{ color: "white", fontWeight: "900", fontSize: 12 }}>Share</Text></Pressable>
          <Pressable onPress={onSave} style={{ alignItems: "center", gap: 4 }}><Ionicons name={reel.viewer_has_saved ? "bookmark" : "bookmark-outline"} size={29} color="white" /><Text style={{ color: "white", fontWeight: "900", fontSize: 12 }}>Save</Text></Pressable>
        </View>
      </View>
    </View>
  );
}
