import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { router } from "expo-router";
import { Controller, useForm } from "react-hook-form";
import { Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { z } from "zod";
import { register } from "../src/api/auth";

const schema = z.object({
  full_name: z.string().min(2),
  username: z.string().min(3).regex(/^[a-zA-Z0-9_]+$/),
  phone_number: z.string().min(8),
  email: z.string().email(),
  date_of_birth: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  password: z.string().min(8),
  confirm_password: z.string().min(8),
  accepted_terms: z.boolean(),
  accepted_privacy: z.boolean(),
}).refine((data) => data.password === data.confirm_password, { path: ["confirm_password"], message: "Passwords must match" });

type FormValues = z.infer<typeof schema>;

const fields: Array<keyof FormValues> = ["full_name", "username", "phone_number", "email", "date_of_birth", "password", "confirm_password"];

export default function RegisterScreen() {
  const { control, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", username: "", phone_number: "", email: "", date_of_birth: "", password: "", confirm_password: "", accepted_terms: true, accepted_privacy: true },
  });
  const mutation = useMutation({
    mutationFn: register,
    onSuccess(result) {
      router.push({ pathname: "/verify", params: { phone: result.data.user.phone_number } });
    },
  });

  return (
    <ScrollView contentContainerStyle={{ padding: 24, paddingTop: 64, gap: 14 }} style={{ backgroundColor: "#FFFFFF" }}>
      <Text style={{ fontSize: 30, fontWeight: "800", color: "#14231F" }}>Create account</Text>
      {fields.map((field) => (
        <View key={field} style={{ gap: 6 }}>
          <Controller control={control} name={field} render={({ field: input }) => (
            <TextInput placeholder={field.replaceAll("_", " ")} secureTextEntry={field.includes("password")} autoCapitalize="none" value={String(input.value)} onChangeText={input.onChange} style={{ borderWidth: 1, borderColor: "#CED9D4", borderRadius: 8, padding: 14 }} />
          )} />
          {errors[field] ? <Text style={{ color: "#B42318" }}>{errors[field]?.message}</Text> : null}
        </View>
      ))}
      {mutation.error ? <Text style={{ color: "#B42318" }}>{mutation.error.message}</Text> : null}
      <Pressable disabled={mutation.isPending} onPress={handleSubmit((values) => mutation.mutate(values))} style={{ backgroundColor: "#126C57", padding: 16, borderRadius: 8, alignItems: "center", opacity: mutation.isPending ? 0.6 : 1 }}>
        <Text style={{ color: "white", fontWeight: "800" }}>{mutation.isPending ? "Creating..." : "Create account"}</Text>
      </Pressable>
    </ScrollView>
  );
}
