import { Audio, AVPlaybackStatus } from "expo-av";
import { useEffect, useRef, useState } from "react";
import { Pressable, Text, View } from "react-native";
import type { MessageAttachment } from "../types/messaging";

const RECORDING_OPTIONS = Audio.RecordingOptionsPresets.HIGH_QUALITY;

export type VoiceUpload = { uri: string; name: string; type: string; kind: "voice_note"; duration?: number };

export function formatDuration(seconds?: number | null) {
  const total = Math.max(0, Math.floor(seconds ?? 0));
  const mins = Math.floor(total / 60).toString().padStart(2, "0");
  const secs = (total % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

function AudioPlayback({ uri, duration }: { uri: string; duration?: number | null }) {
  const sound = useRef<Audio.Sound | null>(null);
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const totalDuration = duration ?? 0;

  useEffect(() => () => { sound.current?.unloadAsync().catch(() => undefined); }, []);

  async function toggle() {
    if (!uri) return;
    if (!sound.current) {
      const loaded = await Audio.Sound.createAsync({ uri }, { shouldPlay: true }, (status: AVPlaybackStatus) => {
        if (!status.isLoaded) return;
        setPlaying(status.isPlaying);
        setPosition(Math.round(status.positionMillis / 1000));
        if (status.didJustFinish) {
          setPlaying(false);
          setPosition(0);
          sound.current?.setPositionAsync(0).catch(() => undefined);
        }
      });
      sound.current = loaded.sound;
      setPlaying(true);
      return;
    }
    const status = await sound.current.getStatusAsync();
    if (status.isLoaded && status.isPlaying) await sound.current.pauseAsync(); else await sound.current.playAsync();
  }

  const pct = totalDuration ? Math.min(100, Math.round((position / totalDuration) * 100)) : 0;
  return <View style={{ marginTop: 8, gap: 6 }}><View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}><Pressable onPress={toggle}><Text style={{ color: "#126C57", fontWeight: "900" }}>{playing ? "Pause" : "Play"}</Text></Pressable><Text style={{ color: "#374151" }}>{formatDuration(position)} / {formatDuration(totalDuration)}</Text></View><View style={{ height: 4, backgroundColor: "#D1D5DB", borderRadius: 2 }}><View style={{ width: `${pct}%`, height: 4, backgroundColor: "#126C57", borderRadius: 2 }} /></View></View>;
}

export function VoiceRecorder({ disabled, onSend, onRecordingChange }: { disabled?: boolean; onSend: (upload: VoiceUpload) => Promise<void>; onRecordingChange?: (active: boolean) => void }) {
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [recordedUri, setRecordedUri] = useState("");
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (timer.current) clearInterval(timer.current); recording?.stopAndUnloadAsync().catch(() => undefined); }, [recording]);

  async function start() {
    setError("");
    const permission = await Audio.requestPermissionsAsync();
    if (!permission.granted) { setError("Microphone permission is required."); return; }
    await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
    const created = await Audio.Recording.createAsync(RECORDING_OPTIONS, (status) => setDuration(Math.round((status.durationMillis ?? 0) / 1000)));
    setRecording(created.recording);
    setRecordedUri("");
    setDuration(0);
    onRecordingChange?.(true);
    timer.current = setInterval(async () => {
      const status = await created.recording.getStatusAsync();
      setDuration(Math.round((status.durationMillis ?? 0) / 1000));
    }, 500);
  }

  async function stop() {
    if (!recording) return;
    if (timer.current) clearInterval(timer.current);
    await recording.stopAndUnloadAsync();
    const status = await recording.getStatusAsync();
    setDuration(Math.round((status.durationMillis ?? 0) / 1000));
    setRecordedUri(recording.getURI() ?? "");
    setRecording(null);
    onRecordingChange?.(false);
  }

  async function cancel() {
    if (timer.current) clearInterval(timer.current);
    await recording?.stopAndUnloadAsync().catch(() => undefined);
    setRecording(null);
    setRecordedUri("");
    setDuration(0);
    setError("");
    onRecordingChange?.(false);
  }

  async function send() {
    if (!recordedUri || sending) return;
    setSending(true);
    setError("");
    try {
      await onSend({ uri: recordedUri, name: `voice-${Date.now()}.m4a`, type: "audio/mp4", kind: "voice_note", duration });
      setRecordedUri("");
      setDuration(0);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Voice note upload failed. Try again.");
    } finally {
      setSending(false);
    }
  }

  return <View style={{ gap: 6 }}>{recording || recordedUri ? <Text style={{ color: "#6B7280" }}>{recording ? "Recording" : "Preview"} {formatDuration(duration)}</Text> : null}{recordedUri ? <AudioPlayback uri={recordedUri} duration={duration} /> : null}<View style={{ flexDirection: "row", gap: 10, alignItems: "center" }}>{recording ? <><Pressable onPress={stop}><Text style={{ color: "#126C57", fontWeight: "900" }}>Stop</Text></Pressable><Pressable onPress={cancel}><Text style={{ color: "#B91C1C", fontWeight: "800" }}>Cancel</Text></Pressable></> : recordedUri ? <><Pressable onPress={send} disabled={sending}><Text style={{ color: "#126C57", fontWeight: "900" }}>{sending ? "Sending" : error ? "Retry" : "Send voice"}</Text></Pressable><Pressable onPress={cancel}><Text style={{ color: "#B91C1C", fontWeight: "800" }}>Discard</Text></Pressable></> : <Pressable disabled={disabled} onPress={start}><Text style={{ color: disabled ? "#9CA3AF" : "#126C57", fontWeight: "900" }}>Voice</Text></Pressable>}</View>{error ? <Text style={{ color: "#B91C1C" }}>{error}</Text> : null}</View>;
}

export function VoiceNotePlayer({ attachment }: { attachment: MessageAttachment }) {
  return <AudioPlayback uri={attachment.url} duration={attachment.duration} />;
}
