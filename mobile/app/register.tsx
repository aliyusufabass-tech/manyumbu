import { Ionicons } from "@expo/vector-icons";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Link, router } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { KeyboardAvoidingView, Platform, Pressable, SafeAreaView, ScrollView, Text, View } from "react-native";
import { z } from "zod";
import { register } from "../src/api/auth";
import { FormField } from "../src/components/FormField";
import { PrimaryButton } from "../src/components/PrimaryButton";
import { colors } from "../src/theme/theme";
import { useAuthStore } from "../src/store/authStore";

const schema = z.object({
  full_name: z.string().min(2, "Enter your full name."),
  username: z.string().min(3, "Username must be at least 3 characters.").regex(/^[a-zA-Z0-9_]+$/, "Use letters, numbers, and underscores only."),
  email: z.string().email("Enter a valid email."),
  phone_number: z.string().min(8, "Enter a valid phone number."),
  date_of_birth: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Use YYYY-MM-DD."),
  password: z.string().min(8, "Password must be at least 8 characters."),
  confirm_password: z.string().min(8, "Confirm your password."),
  accepted_terms: z.boolean().refine(Boolean, "Accept the terms."),
  accepted_privacy: z.boolean().refine(Boolean, "Accept the privacy policy."),
}).refine((data) => data.password === data.confirm_password, { path: ["confirm_password"], message: "Passwords must match." });

type FormValues = z.infer<typeof schema>;

function CheckRow({ checked, label, onPress, error }: { checked: boolean; label: string; onPress: () => void; error?: string }) {
  return <View style={{ gap: 5 }}><Pressable onPress={onPress} style={{ flexDirection: "row", alignItems: "center", gap: 10 }}><View style={{ width: 22, height: 22, borderRadius: 6, borderWidth: 1, borderColor: error ? colors.error : colors.border, backgroundColor: checked ? colors.primary : colors.background, alignItems: "center", justifyContent: "center" }}>{checked ? <Ionicons name="checkmark" size={16} color="white" /> : null}</View><Text style={{ color: colors.text, flex: 1 }}>{label}</Text></Pressable>{error ? <Text style={{ color: colors.error }}>{error}</Text> : null}</View>;
}

export default function RegisterScreen() {
  const setSession = useAuthStore((state) => state.setSession);
  const { control, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", username: "", email: "", phone_number: "", date_of_birth: "", password: "", confirm_password: "", accepted_terms: false, accepted_privacy: false },
  });
  const mutation = useMutation({
    mutationFn: register,
    async onSuccess(result) {
      if (!result.data.access || !result.data.refresh) {
        router.replace("/login");
        return;
      }
      await setSession(result.data.user, { access: result.data.access, refresh: result.data.refresh });
      router.replace("/(tabs)/home");
    },
  });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ padding: 22, paddingTop: 26, gap: 16 }} keyboardShouldPersistTaps="handled">
          <View style={{ gap: 6, marginBottom: 4 }}><Text style={{ color: colors.text, fontSize: 32, fontWeight: "900" }}>Create account</Text><Text style={{ color: colors.muted, fontSize: 16, lineHeight: 22 }}>Join Manyumbu and start sharing with your people.</Text></View>
          <Controller control={control} name="full_name" render={({ field }) => <FormField label="Full name" leftIcon="person-outline" placeholder="Asha Manyumbu" value={field.value} onChangeText={field.onChange} error={errors.full_name?.message} />} />
          <Controller control={control} name="username" render={({ field }) => <FormField label="Username" leftIcon="at-outline" placeholder="asha_manyumbu" autoCapitalize="none" value={field.value} onChangeText={field.onChange} error={errors.username?.message} />} />
          <Controller control={control} name="email" render={({ field }) => <FormField label="Email" leftIcon="mail-outline" placeholder="you@example.com" keyboardType="email-address" autoCapitalize="none" value={field.value} onChangeText={field.onChange} error={errors.email?.message} />} />
          <Controller control={control} name="phone_number" render={({ field }) => <FormField label="Phone number" leftIcon="call-outline" placeholder="0712345678" keyboardType="phone-pad" value={field.value} onChangeText={field.onChange} error={errors.phone_number?.message} />} />
          <Controller control={control} name="date_of_birth" render={({ field }) => <FormField label="Date of birth" leftIcon="calendar-outline" placeholder="YYYY-MM-DD" keyboardType="numbers-and-punctuation" value={field.value} onChangeText={field.onChange} helper="Use the format YYYY-MM-DD." error={errors.date_of_birth?.message} />} />
          <Controller control={control} name="password" render={({ field }) => <FormField label="Password" leftIcon="lock-closed-outline" placeholder="Create a strong password" value={field.value} onChangeText={field.onChange} secureTextEntry secureToggle error={errors.password?.message} />} />
          <Controller control={control} name="confirm_password" render={({ field }) => <FormField label="Confirm password" leftIcon="shield-checkmark-outline" placeholder="Repeat your password" value={field.value} onChangeText={field.onChange} secureTextEntry secureToggle error={errors.confirm_password?.message} />} />
          <CheckRow checked={watch("accepted_terms")} label="I agree to the Terms of service" onPress={() => setValue("accepted_terms", !watch("accepted_terms"), { shouldValidate: true })} error={errors.accepted_terms?.message} />
          <CheckRow checked={watch("accepted_privacy")} label="I agree to the Privacy policy" onPress={() => setValue("accepted_privacy", !watch("accepted_privacy"), { shouldValidate: true })} error={errors.accepted_privacy?.message} />
          {mutation.error ? <Text style={{ color: colors.error }}>{mutation.error.message}</Text> : null}
          <PrimaryButton title="Create account" loading={mutation.isPending} onPress={handleSubmit((values) => mutation.mutate(values))} />
          <Link href="/login" asChild><Pressable style={{ alignItems: "center", padding: 8 }}><Text style={{ color: colors.muted }}>Already have an account? <Text style={{ color: colors.primary, fontWeight: "900" }}>Sign in</Text></Text></Pressable></Link>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}