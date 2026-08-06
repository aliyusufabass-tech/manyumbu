import { Ionicons } from "@expo/vector-icons";
import { ReactNode, useState } from "react";
import { Pressable, Text, TextInput, TextInputProps, View } from "react-native";
import { colors } from "../theme/theme";

export function FormField({ label, error, helper, leftIcon, secureToggle, right, ...props }: TextInputProps & { label: string; error?: string; helper?: string; leftIcon?: keyof typeof Ionicons.glyphMap; secureToggle?: boolean; right?: ReactNode }) {
  const [hidden, setHidden] = useState(Boolean(props.secureTextEntry));
  return (
    <View style={{ gap: 7 }}>
      <Text style={{ color: colors.text, fontWeight: "800" }}>{label}</Text>
      <View style={{ minHeight: 52, borderWidth: 1, borderColor: error ? colors.error : colors.border, backgroundColor: colors.background, borderRadius: 14, paddingHorizontal: 13, flexDirection: "row", alignItems: "center", gap: 10 }}>
        {leftIcon ? <Ionicons name={leftIcon} size={20} color={colors.muted} /> : null}
        <TextInput {...props} secureTextEntry={secureToggle ? hidden : props.secureTextEntry} placeholderTextColor={colors.muted} style={[{ flex: 1, color: colors.text, fontSize: 16, paddingVertical: 12 }, props.style]} />
        {secureToggle ? <Pressable onPress={() => setHidden(!hidden)} hitSlop={10}><Ionicons name={hidden ? "eye-outline" : "eye-off-outline"} size={21} color={colors.muted} /></Pressable> : right}
      </View>
      {error ? <Text style={{ color: colors.error }}>{error}</Text> : helper ? <Text style={{ color: colors.muted }}>{helper}</Text> : null}
    </View>
  );
}