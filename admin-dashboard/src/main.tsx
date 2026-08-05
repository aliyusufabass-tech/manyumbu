import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, Bell, BriefcaseBusiness, Gavel, LockKeyhole, Phone, RotateCcw, ShieldCheck, Trash2, Users } from "lucide-react";
import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { adminLogin } from "./api/auth";
import { fetchAdminPosts, moderatePost } from "./api/posts";
import { fetchAdminReels, fetchAdminStories, moderateStoryReel } from "./api/phase4";
import { fetchMessageReports, moderateMessageReport } from "./api/messaging";
import { fetchAdminGroups, fetchGroupReports, moderateGroup, sendAnnouncement } from "./api/groups";
import { createUserRestriction, decideAppeal, decideVerification, fetchAppeals, fetchCallReports, fetchModerationQueue, fetchProfessionalAccounts, fetchVerificationRequests, professionalAction } from "./api/phase7";
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
function MessageReportsPanel({ token }: { token: string }) {
  const client = useQueryClient();
  const [kind, setKind] = useState<"messages" | "conversations">("messages");
  const [status, setStatus] = useState("");
  const reports = useQuery({ queryKey: ["message-reports", kind, status], queryFn: () => fetchMessageReports(token, kind, status) });
  const moderation = useMutation({ mutationFn: ({ id, action }: { id: number; action: "pending" | "review" | "resolve" | "reject" }) => moderateMessageReport(token, kind, id, action, "Admin dashboard action"), onSuccess: () => client.invalidateQueries({ queryKey: ["message-reports"] }) });
  return <section className="content-panel"><div className="toolbar"><h2>Private Message Reports</h2><select value={kind} onChange={(event) => setKind(event.target.value as "messages" | "conversations")}><option value="messages">Messages</option><option value="conversations">Conversations</option></select><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option><option value="pending">Pending</option><option value="under_review">Under review</option><option value="resolved">Resolved</option><option value="rejected">Rejected</option></select></div>{reports.isLoading ? <p>Loading reports...</p> : null}{reports.isError ? <p className="error">Reports could not be loaded.</p> : null}<div className="table">{(reports.data?.data.results ?? []).map((report) => <div className="row" key={`${kind}-${report.id}`}><div><strong>{report.reason}</strong><p>{report.details || "No details supplied."}</p><small>{report.status} · reporter @{report.reporter.username} · {report.message_id ?? report.conversation_id}</small></div><div className="actions"><button onClick={() => moderation.mutate({ id: report.id, action: "review" })}>Review</button><button onClick={() => moderation.mutate({ id: report.id, action: "resolve" })}>Resolve</button><button onClick={() => moderation.mutate({ id: report.id, action: "reject" })}>Reject</button></div></div>)}</div></section>;
}
function GroupModerationPanel({ token }: { token: string }) {
  const client = useQueryClient();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [reportKind, setReportKind] = useState<"group-reports" | "group-message-reports">("group-reports");
  const [title, setTitle] = useState("Service update");
  const [body, setBody] = useState("");
  const groups = useQuery({ queryKey: ["admin-groups", q, status], queryFn: () => fetchAdminGroups(token, { q, status }) });
  const reports = useQuery({ queryKey: ["admin-group-reports", reportKind], queryFn: () => fetchGroupReports(token, reportKind) });
  const moderation = useMutation({ mutationFn: ({ id, action }: { id: string; action: "suspend" | "restore" | "remove" | "warn-owner" }) => moderateGroup(token, id, action, "Admin dashboard action"), onSuccess: () => client.invalidateQueries({ queryKey: ["admin-groups"] }) });
  const announcement = useMutation({ mutationFn: () => sendAnnouncement(token, title, body), onSuccess: () => setBody("") });
  return <section className="content-panel"><div className="toolbar"><h2><Users size={20} /> Groups</h2><input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Search groups" /><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option><option value="active">Active</option><option value="suspended">Suspended</option><option value="deleted">Deleted</option></select></div>{groups.isError ? <p className="error">Groups could not be loaded.</p> : null}<div className="table">{(groups.data?.data.results ?? []).map((group) => <div className="row" key={group.id}><div><strong>{group.name}</strong><p>{group.description || "No description"}</p><small>{group.status} · {group.privacy} · {group.member_count} members · owner @{group.owner.username}</small></div><div className="actions"><button onClick={() => moderation.mutate({ id: group.id, action: "suspend" })}>Suspend</button><button onClick={() => moderation.mutate({ id: group.id, action: "restore" })}><RotateCcw size={16} /> Restore</button><button onClick={() => moderation.mutate({ id: group.id, action: "warn-owner" })}><Bell size={16} /> Warn</button><button onClick={() => moderation.mutate({ id: group.id, action: "remove" })}><Trash2 size={16} /> Remove</button></div></div>)}</div><div className="toolbar"><h2>Group Reports</h2><select value={reportKind} onChange={(event) => setReportKind(event.target.value as "group-reports" | "group-message-reports")}><option value="group-reports">Groups</option><option value="group-message-reports">Messages</option></select><span /></div><div className="table">{(reports.data?.data.results ?? []).map((report) => <div className="row" key={`${reportKind}-${report.id}`}><div><strong>{report.reason}</strong><p>{report.group_name ?? report.group_id}</p><small>{report.status} · reporter @{report.reporter.username} · {report.message_id ?? report.group_id}</small></div></div>)}</div><div className="toolbar"><h2>Announcement</h2><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Title" /><button disabled={!body || announcement.isPending} onClick={() => announcement.mutate()}><Bell size={16} /> Send</button></div><textarea value={body} onChange={(event) => setBody(event.target.value)} placeholder="Write an in-app announcement" /></section>;
}
function PhaseSevenPanel({ token }: { token: string }) {
  const client = useQueryClient();
  const [username, setUsername] = useState("");
  const [feature, setFeature] = useState("start_call");
  const [reason, setReason] = useState("Policy review");
  const queue = useQuery({ queryKey: ["moderation-queue"], queryFn: () => fetchModerationQueue(token) });
  const calls = useQuery({ queryKey: ["call-reports"], queryFn: () => fetchCallReports(token) });
  const appeals = useQuery({ queryKey: ["appeals"], queryFn: () => fetchAppeals(token) });
  const verification = useQuery({ queryKey: ["verification-requests"], queryFn: () => fetchVerificationRequests(token) });
  const professional = useQuery({ queryKey: ["professional-accounts"], queryFn: () => fetchProfessionalAccounts(token) });
  const appealDecision = useMutation({ mutationFn: ({ id, action }: { id: string; action: "approved" | "partially_approved" | "rejected" }) => decideAppeal(token, id, action, reason), onSuccess: () => { client.invalidateQueries({ queryKey: ["appeals"] }); client.invalidateQueries({ queryKey: ["moderation-queue"] }); } });
  const verifyDecision = useMutation({ mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" }) => decideVerification(token, id, action, reason), onSuccess: () => { client.invalidateQueries({ queryKey: ["verification-requests"] }); client.invalidateQueries({ queryKey: ["moderation-queue"] }); } });
  const restrict = useMutation({ mutationFn: () => createUserRestriction(token, username, feature, reason), onSuccess: () => { setUsername(""); client.invalidateQueries({ queryKey: ["moderation-queue"] }); } });
  const profAction = useMutation({ mutationFn: ({ user, action }: { user: string; action: "remove-creator" | "remove-business" | "remove-verification" }) => professionalAction(token, user, action), onSuccess: () => client.invalidateQueries({ queryKey: ["professional-accounts"] }) });
  return <section className="content-panel"><div className="toolbar"><h2><Gavel size={20} /> Phase 7 Moderation</h2><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Decision reason" /><span /></div><h3>Unified queue</h3><div className="table">{(queue.data?.data.results ?? []).map((item) => <div className="row" key={`${item.kind}-${item.id}`}><div><strong>{item.kind}</strong><p>{item.reason}</p><small>{item.status} · @{item.reporter.username} · {item.object_id}</small></div></div>)}</div><h3><Phone size={18} /> Call reports</h3><div className="table">{(calls.data?.data.results ?? []).map((item) => <div className="row" key={`call-${String(item.id)}`}><div><strong>{String(item.reason)}</strong><p>{String(item.details ?? "No details")}</p><small>{String(item.status)} · {String(item.call_id)}</small></div></div>)}</div><h3>Appeals</h3><div className="table">{(appeals.data?.data.results ?? []).map((item) => <div className="row" key={`appeal-${String(item.id)}`}><div><strong>{String(item.status)}</strong><p>{String(item.explanation)}</p><small>{String(item.id)}</small></div><div className="actions"><button onClick={() => appealDecision.mutate({ id: String(item.id), action: "approved" })}>Approve</button><button onClick={() => appealDecision.mutate({ id: String(item.id), action: "rejected" })}>Reject</button></div></div>)}</div><h3><BadgeCheck size={18} /> Verification</h3><div className="table">{(verification.data?.data.results ?? []).map((item) => <div className="row" key={`verify-${String(item.id)}`}><div><strong>{String(item.public_name)}</strong><p>{String(item.reason)}</p><small>{String(item.status)} · {String(item.account_type)}</small></div><div className="actions"><button onClick={() => verifyDecision.mutate({ id: String(item.id), action: "approve" })}>Approve</button><button onClick={() => verifyDecision.mutate({ id: String(item.id), action: "reject" })}>Reject</button></div></div>)}</div><h3><BriefcaseBusiness size={18} /> Professional accounts</h3><div className="table">{(professional.data?.data.results ?? []).map((item) => { const user = item.user as { username: string; full_name: string }; return <div className="row" key={`professional-${user.username}`}><div><strong>{user.full_name}</strong><p>{String(item.account_type)} · {String(item.category)}</p><small>@{user.username} · {String(item.status)}</small></div><div className="actions"><button onClick={() => profAction.mutate({ user: user.username, action: "remove-verification" })}>Remove badge</button><button onClick={() => profAction.mutate({ user: user.username, action: "remove-creator" })}>Remove creator</button><button onClick={() => profAction.mutate({ user: user.username, action: "remove-business" })}>Remove business</button></div></div>; })}</div><h3>User restriction</h3><div className="toolbar"><input value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Username" /><select value={feature} onChange={(event) => setFeature(event.target.value)}><option value="start_call">Cannot start calls</option><option value="receive_call">Cannot receive calls</option><option value="professional">No professional features</option><option value="message">No messages</option><option value="create_group">No group creation</option></select><button disabled={!username || restrict.isPending} onClick={() => restrict.mutate()}>Restrict</button></div></section>;
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
      {token ? <><PostsPanel token={token} /><StoriesReelsPanel token={token} /><MessageReportsPanel token={token} /><GroupModerationPanel token={token} /><PhaseSevenPanel token={token} /></> : null}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><QueryClientProvider client={queryClient}><AdminApp /></QueryClientProvider></React.StrictMode>);
