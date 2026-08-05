import { QueryClient, QueryClientProvider, useMutation } from "@tanstack/react-query";
import { LockKeyhole, ShieldCheck } from "lucide-react";
import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { adminLogin } from "./api/auth";
import "./styles.css";

const queryClient = new QueryClient();

function AdminApp() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const mutation = useMutation({ mutationFn: () => adminLogin(identifier, password) });
  const user = mutation.data?.data.user;

  return (
    <main className="page">
      <section className="login-panel">
        <div className="mark"><ShieldCheck size={30} /></div>
        <h1>Manyumbu Admin</h1>
        <p>Secure moderation and account operations begin with staff authentication.</p>
        <label>
          Login identifier
          <input value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="phone, email, or username" />
        </label>
        <label>
          Password
          <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" placeholder="password" />
        </label>
        {mutation.error ? <div className="error">{mutation.error.message}</div> : null}
        {user ? <div className="success">Signed in as {user.username}</div> : null}
        <button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
          <LockKeyhole size={18} /> {mutation.isPending ? "Checking..." : "Sign in"}
        </button>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AdminApp />
    </QueryClientProvider>
  </React.StrictMode>
);
