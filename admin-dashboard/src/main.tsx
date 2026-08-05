import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LockKeyhole, RotateCcw, ShieldCheck, Trash2 } from "lucide-react";
import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { adminLogin } from "./api/auth";
import { fetchAdminPosts, moderatePost } from "./api/posts";
import { fetchAdminReels, fetchAdminStories, moderateStoryReel } from "./api/phase4";
import "./styles.css";

const queryClient = new QueryClient();

function PostsPanel({ token }: { token: string }) {
  const client = useQueryClient();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const posts = useQuery({ queryKey: ["admin-posts", q, status], queryFn: () => fetchAdminPosts(token, { q, status }) });
  const moderation = useMutation({ mutationFn: ({ id, action }: { id: string; action: "remove" | "restore" }) => moderatePost(token, id, action, "Admin dashboard action"), onSuccess: () => client.invalidateQueries({ queryKey: ["admin-posts"] }) });

  return (
    <section className="content-panel">
      <div className="toolbar"><h2>Posts</h2><input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Search posts or authors" /><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option><option value="published">Published</option><option value="archived">Archived</option><option value="removed">Removed</option><option value="deleted">Deleted</option></select></div>
      {posts.isLoading ? <p>Loading posts...</p> : null}
      {posts.isError ? <p className="error">Posts could not be loaded.</p> : null}
      <div className="table">
        {(posts.data?.data.results ?? []).map((post) => <div className="row" key={post.id}><div><strong>{post.author.username}</strong><p>{post.caption || "Media post"}</p><small>{post.status} · {post.post_type} · {post.like_count} likes · {post.comment_count} comments</small></div><div className="actions"><button onClick={() => moderation.mutate({ id: post.id, action: "remove" })}><Trash2 size={16} /> Remove</button><button onClick={() => moderation.mutate({ id: post.id, action: "restore" })}><RotateCcw size={16} /> Restore</button></div></div>)}
      </div>
    </section>
  );
}

function StoriesReelsPanel({ token }: { token: string }) {
  const client = useQueryClient();
  const stories = useQuery({ queryKey: ["admin-stories"], queryFn: () => fetchAdminStories(token) });
  const reels = useQuery({ queryKey: ["admin-reels"], queryFn: () => fetchAdminReels(token) });
  const moderation = useMutation({ mutationFn: ({ kind, id, action }: { kind: "stories" | "reels"; id: string; action: "remove" | "restore" | "retry-processing" }) => moderateStoryReel(token, kind, id, action, "Admin dashboard action"), onSuccess: () => { client.invalidateQueries({ queryKey: ["admin-stories"] }); client.invalidateQueries({ queryKey: ["admin-reels"] }); } });
  return <section className="content-panel"><div className="toolbar"><h2>Stories and Reels</h2></div><h3>Stories</h3><div className="table">{(stories.data?.data.results ?? []).map((story) => <div className="row" key={story.id}><div><strong>{story.author.username}</strong><p>{story.caption || story.story_type}</p><small>{story.status} · {story.view_count} views</small></div><div className="actions"><button onClick={() => moderation.mutate({ kind: "stories", id: story.id, action: "remove" })}>Remove</button><button onClick={() => moderation.mutate({ kind: "stories", id: story.id, action: "restore" })}>Restore</button></div></div>)}</div><h3>Reels</h3><div className="table">{(reels.data?.data.results ?? []).map((reel) => <div className="row" key={reel.id}><div><strong>{reel.author.username}</strong><p>{reel.caption || "Reel"}</p><small>{reel.status} · {reel.processing_status} · {reel.view_count} views</small></div><div className="actions"><button onClick={() => moderation.mutate({ kind: "reels", id: reel.id, action: "remove" })}>Remove</button><button onClick={() => moderation.mutate({ kind: "reels", id: reel.id, action: "restore" })}>Restore</button><button onClick={() => moderation.mutate({ kind: "reels", id: reel.id, action: "retry-processing" })}>Retry</button></div></div>)}</div></section>;
}
function AdminApp() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const mutation = useMutation({ mutationFn: () => adminLogin(identifier, password), onSuccess: (result) => setToken(result.data.tokens.access) });
  const user = mutation.data?.data.user;

  return (
    <main className="page">
      <section className="login-panel">
        <div className="mark"><ShieldCheck size={30} /></div>
        <h1>Manyumbu Admin</h1>
        <p>Secure moderation and account operations begin with staff authentication.</p>
        <label>Login identifier<input value={identifier} onChange={(event) => setIdentifier(event.target.value)} placeholder="phone, email, or username" /></label>
        <label>Password<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" placeholder="password" /></label>
        {mutation.error ? <div className="error">{mutation.error.message}</div> : null}
        {user ? <div className="success">Signed in as {user.username}</div> : null}
        <button disabled={mutation.isPending} onClick={() => mutation.mutate()}><LockKeyhole size={18} /> {mutation.isPending ? "Checking..." : "Sign in"}</button>
      </section>
      {token ? <><PostsPanel token={token} /><StoriesReelsPanel token={token} /></> : null}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><QueryClientProvider client={queryClient}><AdminApp /></QueryClientProvider></React.StrictMode>);

