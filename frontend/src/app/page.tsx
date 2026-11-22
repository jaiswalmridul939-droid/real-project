"use client";

import { FormEvent, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Bell, Mic } from "lucide-react";
import { api, Match, Profile, Scheme } from "@/lib/api";
import { ProfileEditor } from "@/components/ProfileEditor";

const AdminWorkbench = dynamic(() => import("@/components/AdminWorkbench").then((module) => module.AdminWorkbench), {
  loading: () => <div className="workbench-skeleton" aria-label="Loading admin tools" />,
});

type Screen = "home" | "describe" | "profile" | "results" | "detail" | "dashboard" | "outbox" | "admin" | "partners";
type Language = "en" | "mr" | "hi";
type DashboardData = { applications: { id: number; scheme_id: number; scheme_name: string; status: string }[]; upcoming_deadlines: { scheme_id: number; scheme_name: string; deadline_date: string; days_left: number; urgent: boolean }[]; checklist: { doc_name: string; where_to_get: string; scheme_count: number; is_ready: boolean }[]; notification_count: number };

const words = {
  en: { start: "Start", heroTitle: "Find support for your farm.", heroSubtitle: "Understand your next step.", heroCount: "public schemes", heroCopy: "matched to your situation, with clear reasons and official sources.", stepOne: "Tell us what matters", stepTwo: "Check your matches", stepThree: "Take your next step", exampleText: "Example: I have 2 acres in Nashik, a small income and a bank account.", review: "Review your details", editStory: "← Edit story", oneQuestion: "ONE QUICK QUESTION", story: "Tell us about your farm and family", results: "My matches", dashboard: "My dashboard", outbox: "Outbox", admin: "Admin", partners: "For partners", next: "Find my schemes", confirm: "See my results", privacy: "Only share details needed for matching. Never enter Aadhaar, PAN or any 12-digit ID. If enabled, Claude processes this text for profile facts only; it never decides eligibility.", estimate: "This is an estimate. Final eligibility is decided by the official authority.", documents: "Documents to keep ready", apply: "Start application", delete: "Delete my data", voice: "Speak your situation" },
  mr: { start: "सुरू करा", heroTitle: "तुमच्या शेतीसाठी मदत शोधा.", heroSubtitle: "पुढचे पाऊल समजून घ्या.", heroCount: "सार्वजनिक योजना", heroCopy: "स्पष्ट कारणे आणि अधिकृत स्रोतांसह.", stepOne: "तुमची गरज सांगा", stepTwo: "जुळणाऱ्या योजना पहा", stepThree: "पुढचे पाऊल घ्या", exampleText: "उदाहरण: नाशिकमध्ये माझी २ एकर जमीन आहे, उत्पन्न कमी आहे आणि बँक खाते आहे.", review: "तुमचे तपशील तपासा", editStory: "← माहिती बदला", oneQuestion: "एक छोटा प्रश्न", story: "तुमच्या शेती आणि कुटुंबाबद्दल सांगा", results: "माझ्या योजना", dashboard: "माझे डॅशबोर्ड", outbox: "सूचना पेटी", admin: "प्रशासन", partners: "भागीदारांसाठी", next: "योजना शोधा", confirm: "माझे निकाल पहा", privacy: "फक्त आवश्यक माहिती सांगा. आधार, पॅन किंवा १२ अंकी क्रमांक टाकू नका. Claude सुरू असल्यास तो फक्त माहितीचे तपशील काढतो; पात्रता ठरवत नाही.", estimate: "हा अंदाज आहे. अंतिम पात्रता अधिकृत अधिकारी ठरवतील.", documents: "तयार ठेवायची कागदपत्रे", apply: "अर्ज सुरू करा", delete: "माझी माहिती हटवा", voice: "तुमची परिस्थिती बोला" },
  hi: { start: "शुरू करें", heroTitle: "अपने खेत के लिए सहायता खोजें।", heroSubtitle: "अगला कदम समझें।", heroCount: "सार्वजनिक योजनाएं", heroCopy: "साफ कारणों और आधिकारिक स्रोतों के साथ।", stepOne: "अपनी जरूरत बताएं", stepTwo: "मेल खाती योजनाएं देखें", stepThree: "अगला कदम लें", exampleText: "उदाहरण: नासिक में मेरी 2 एकड़ जमीन है, आय कम है और बैंक खाता है।", review: "अपनी जानकारी देखें", editStory: "← जानकारी बदलें", oneQuestion: "एक छोटा सवाल", story: "अपने खेत और परिवार के बारे में बताएं", results: "मेरी योजनाएं", dashboard: "मेरा डैशबोर्ड", outbox: "सूचना पेटी", admin: "प्रशासन", partners: "साझेदारों के लिए", next: "योजनाएं खोजें", confirm: "मेरे नतीजे देखें", privacy: "केवल जरूरी जानकारी दें। आधार, पैन या 12 अंकों की ID न डालें। Claude चालू होने पर वह सिर्फ प्रोफ़ाइल तथ्य निकालता है, पात्रता तय नहीं करता।", estimate: "यह एक अनुमान है। अंतिम पात्रता आधिकारिक अधिकारी तय करते हैं।", documents: "तैयार रखने वाले दस्तावेज़", apply: "आवेदन शुरू करें", delete: "मेरा डेटा हटाएं", voice: "अपनी स्थिति बोलें" },
} as const;
const demoNotice: Record<Language, string> = {
  en: "Synthetic profiles and sample scheme summaries. Source links were checked where reachable; eligibility rules and deadlines still need confirmation.",
  mr: "नमुना योजना आणि कृत्रिम प्रोफाइल. उपलब्ध स्रोत तपासले आहेत; पात्रतेचे नियम आणि अर्जाच्या तारखा अधिकृत ठिकाणी पुन्हा तपासा.",
  hi: "नमूना योजनाएं और कृत्रिम प्रोफ़ाइल। उपलब्ध स्रोत जांचे गए हैं; पात्रता नियम और आवेदन तिथियां आधिकारिक स्रोत से दोबारा जांचें.",
};
const fieldLabels: Record<string, string> = { state: "State", district: "District", age: "Age", gender: "Gender", land_acres: "Land (acres)", land_ownership: "Land status", income_band: "Income band", category: "Category", has_bank_account: "Bank account", is_woman: "Woman farmer", crops: "Crops", family_size: "Family size", occupation: "Occupation" };
const statusClass = (status: string) => status === "Likely eligible" ? "good" : status === "Likely not eligible" ? "bad" : "maybe";
const formatDate = (value: string, language: Language) => new Date(`${value}T00:00:00`).toLocaleDateString(language === "mr" ? "mr-IN" : language === "hi" ? "hi-IN" : "en-IN", { day: "2-digit", month: "short", year: "numeric" });

export default function Home() {
  const [language, setLanguage] = useState<Language>("en");
  const [screen, setScreen] = useState<Screen>("home");
  const [description, setDescription] = useState("");
  const [profile, setProfile] = useState<Profile>({ state: "Maharashtra", occupation: "farmer" });
  const [missing, setMissing] = useState<string[]>([]);
  const [userId, setUserId] = useState<number | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [selected, setSelected] = useState<Match | null>(null);
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [readyDocs, setReadyDocs] = useState<Record<string, boolean>>({});
  const [reminderDate, setReminderDate] = useState("");
  const [messages, setMessages] = useState<{ id: number; channel: string; body: string; created_at: string | null }[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [token, setToken] = useState("");
  const [adminSchemes, setAdminSchemes] = useState<Scheme[]>([]);
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [ruleField, setRuleField] = useState("land_acres");
  const [ruleValue, setRuleValue] = useState("5");
  const t = words[language];

  useEffect(() => {
    void Promise.resolve().then(() => {
      const savedId = localStorage.getItem("cwy-user-id");
      if (savedId) setUserId(Number(savedId));
      const savedLanguage = localStorage.getItem("cwy-language") as Language | null;
      if (savedLanguage && ["en", "mr", "hi"].includes(savedLanguage)) setLanguage(savedLanguage);
      const cached = localStorage.getItem("cwy-schemes");
      if (cached) setSchemes(JSON.parse(cached) as Scheme[]);
    });
    api<Scheme[]>("/api/schemes").then((items) => { setSchemes(items); localStorage.setItem("cwy-schemes", JSON.stringify(items)); }).catch(() => undefined);
    if ("serviceWorker" in navigator) void navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  }, []);

  async function extract(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const result = await api<{ profile: Profile; missing_fields: string[] }>("/api/profile/extract", { method: "POST", body: JSON.stringify({ text: description, language }) });
      setProfile({ state: "Maharashtra", occupation: "farmer", ...result.profile }); setMissing(result.missing_fields.slice(0, 3)); setScreen("profile");
    } catch (issue) { setError(issue instanceof Error ? issue.message : "Could not read those details."); } finally { setBusy(false); }
  }

  async function confirmProfile() {
    setBusy(true); setError("");
    try {
      const saved = await api<{ user_id: number; profile_id: number }>("/api/profile", { method: "POST", body: JSON.stringify({ ...profile, language, raw_text: description }) });
      setUserId(saved.user_id); localStorage.setItem("cwy-user-id", String(saved.user_id));
      const result = await api<{ matches: Match[] }>("/api/match", { method: "POST", body: JSON.stringify({ profile_id: saved.profile_id }) });
      setMatches(result.matches); setScreen("results");
    } catch (issue) { setError(issue instanceof Error ? issue.message : "Could not save your profile."); } finally { setBusy(false); }
  }

  async function openDashboard() {
    if (!userId) return setScreen("describe");
    try { setDashboard(await api<DashboardData>(`/api/dashboard?user_id=${userId}`)); } catch (issue) { setError(String(issue)); }
    setScreen("dashboard");
  }

  async function startApplication(match: Match) {
    if (!userId) return setError("Confirm your profile first.");
    setBusy(true);
    try { await api("/api/applications", { method: "POST", body: JSON.stringify({ user_id: userId, scheme_id: match.scheme.id }) }); setSelected(match); await openDashboard(); }
    catch (issue) { setError(issue instanceof Error ? issue.message : "Could not start application."); } finally { setBusy(false); }
  }

  async function toggleDocument(name: string, ready: boolean) {
    if (!userId) return;
    await api("/api/checklist", { method: "POST", body: JSON.stringify({ user_id: userId, doc_name: name, is_ready: ready }) });
    setReadyDocs((current) => ({ ...current, [name.toLowerCase()]: ready }));
    setDashboard(await api<DashboardData>(`/api/dashboard?user_id=${userId}`));
  }

  async function loadDocumentChecks() {
    if (!userId) return;
    const checklist = await api<{ doc_name: string; is_ready: boolean }[]>(`/api/checklist?user_id=${userId}`);
    setReadyDocs(Object.fromEntries(checklist.map((item) => [item.doc_name.toLowerCase(), item.is_ready])));
  }

  async function savePersonalReminder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!userId || !dashboard?.applications.length) return;
    const schemeId = dashboard.applications[0].scheme_id;
    await api("/api/reminders", { method: "POST", body: JSON.stringify({ user_id: userId, scheme_id: schemeId, remind_on: reminderDate, message: `Reminder to check your ${dashboard.applications[0].scheme_name} application and official deadline.` }) });
    setError("Personal reminder saved."); setReminderDate("");
  }

  async function loadOutbox() {
    try { setMessages(await api(`/api/outbox${userId ? `?user_id=${userId}` : ""}`)); } catch (issue) { setError(String(issue)); }
    setScreen("outbox");
  }

  async function openDetails(match: Match) {
    setBusy(true);
    try {
      const scheme = await api<Scheme>(`/api/schemes/${match.scheme.id}`);
      setSelected({ ...match, scheme });
      await loadDocumentChecks();
      setScreen("detail");
    } catch (issue) { setError(issue instanceof Error ? issue.message : "Could not load scheme details."); }
    finally { setBusy(false); }
  }

  function voiceInput() {
    type Recognition = { lang: string; onresult: (event: { results: { 0: { transcript: string } }[] }) => void; start: () => void };
    const voiceWindow = window as Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
    const Speech = voiceWindow.SpeechRecognition ?? voiceWindow.webkitSpeechRecognition;
    if (!Speech) return setError("Voice input is not available in this browser.");
    const recognition = new Speech(); recognition.lang = language === "mr" ? "mr-IN" : language === "hi" ? "hi-IN" : "en-IN";
    recognition.onresult = (event) => setDescription((value) => `${value} ${event.results[0][0].transcript}`.trim()); recognition.start();
  }

  async function adminLogin(event: FormEvent) {
    event.preventDefault();
    try {
      const result = await api<{ access_token: string }>("/api/admin/login", { method: "POST", body: JSON.stringify({ email: adminEmail, password: adminPassword }) });
      setToken(result.access_token);
      const items = await api<Scheme[]>("/api/admin/schemes", { headers: { Authorization: `Bearer ${result.access_token}` } });
      setAdminSchemes(items);
    } catch (issue) { setError(issue instanceof Error ? issue.message : "Sign-in failed."); }
  }

  function renderCard(match: Match) {
    const old = match.scheme.is_outdated ?? false;
    const name = language === "mr" ? match.scheme.name_mr || match.scheme.name_en : language === "hi" ? match.scheme.name_hi || match.scheme.name_en : match.scheme.name_en;
    return <article className="scheme-card" key={match.scheme.id}>
      <div className="card-top"><span className={`status-pill ${statusClass(match.status)}`}>{match.status}</span><span>{match.scheme.level.toUpperCase()}</span></div>
      <h2>{name}</h2><p>{match.scheme.benefit_summary}</p>
      <div className="reason-list">{match.reasoning.slice(0, 3).map((reason, index) => <div key={`${reason.field}-${index}`}><span className={`reason-dot ${reason.result}`} />{reason.explanation || `${fieldLabels[reason.field] ?? reason.field}: ${reason.result}`}</div>)}</div>
      <div className="source-row">{match.scheme.source_name}<span>Last verified: {formatDate(match.scheme.last_verified_date, language)}</span></div>
      {old && <p className="old-warning">May be outdated, check official site</p>}
      <a href={match.scheme.official_url} target="_blank" rel="noreferrer">Official source ↗</a>
      <button className="text-button" onClick={() => void openDetails(match)}>View details →</button>
      <small className="disclaimer">{t.estimate}</small>
    </article>;
  }

  return <main className="app-shell">
    <header className="topbar"><button className="brand" onClick={() => setScreen("home")}><b>C</b><span>CLAIM<br />WHAT&apos;S YOURS</span></button><nav><button onClick={openDashboard}>{t.dashboard}</button><button onClick={loadOutbox}>{t.outbox}</button><button onClick={() => setScreen("partners")}>{t.partners}</button><button onClick={() => setScreen("admin")}>{t.admin}</button></nav><select aria-label="Language" value={language} onChange={(event) => { const selectedLanguage = event.target.value as Language; setLanguage(selectedLanguage); localStorage.setItem("cwy-language", selectedLanguage); }}><option value="en">English</option><option value="mr">मराठी</option><option value="hi">हिन्दी</option></select><button className="bell" aria-label="Notifications" onClick={openDashboard}><Bell size={18} aria-hidden="true" />{dashboard?.notification_count ? ` ${dashboard.notification_count}` : ""}</button></header>
    <aside className="demo-data-notice"><strong>DEMO DATA</strong><span>{demoNotice[language]}</span></aside>
    {error && <div className="toast" role="status">{error}<button onClick={() => setError("")}>×</button></div>}

    {screen === "home" && <><section className="landing"><div><p className="eyebrow">MAHARASHTRA FARMER SUPPORT</p><h1>{t.heroTitle}<br /><em>{t.heroSubtitle}</em></h1><p className="lead">{schemes.length || 10} {t.heroCount}, {t.heroCopy}</p><button className="primary" onClick={() => setScreen("describe")}>{t.start}<span>→</span></button><small>MINIMAL DETAILS · NO ID NUMBERS</small></div><div className="field-art"><div className="sun"/><div className="row row-a"/><div className="row row-b"/><div className="row row-c"/><span className="art-stamp">YOUR<br />NEXT<br />STEP</span><p>{t.heroSubtitle}</p></div></section><div className="steps-band"><span>01 &nbsp; {t.stepOne}</span><span>02 &nbsp; {t.stepTwo}</span><span>03 &nbsp; {t.stepThree}</span></div></>}

    {screen === "describe" && <section className="page narrow"><button className="back" onClick={() => setScreen("home")}>{t.editStory}</button><p className="eyebrow">YOUR STORY, YOUR WORDS</p><h1>{t.story}</h1><form onSubmit={extract}><div className="story-box"><textarea required maxLength={4000} value={description} onChange={(event) => setDescription(event.target.value)} placeholder={t.exampleText} aria-label={t.story}/><button type="button" title={t.voice} aria-label={t.voice} onClick={voiceInput}><Mic size={19} aria-hidden="true" /></button></div><p className="privacy">✳ &nbsp;{t.privacy}</p><div className="examples"><button type="button" onClick={() => setDescription("Mere paas 2 acre zameen hai Nashik mein, income kam hai, bank account hai.")}>2 acres · Nashik · bank account</button><button type="button" onClick={() => setDescription("मी नांदेडमध्ये कापूस शेती करते. माझ्याकडे १ एकर जमीन आहे.")}>Cotton farmer · Nanded</button></div><button className="primary" disabled={busy}>{busy ? "Checking…" : t.next}<span>→</span></button></form></section>}

    {screen === "profile" && <section className="page narrow"><button className="back" onClick={() => setScreen("describe")}>← Edit story</button><p className="eyebrow">CHECK BEFORE WE MATCH</p><h1>Review your details</h1>{missing.length > 0 && <div className="question"><span>ONE QUICK QUESTION · {4 - missing.length} OF 3</span><h2>{missing[0] === "land_acres" ? "About how much land do you farm?" : missing[0] === "district" ? "Which district is your farm in?" : missing[0] === "land_ownership" ? "Do you own or rent your land?" : missing[0] === "has_bank_account" ? "Do you have a bank account?" : "Would you like to share your category?"}</h2><div className="choice-row">{(missing[0] === "land_acres" ? ["Under 1", "1–2", "2–5", "Over 5 acres"] : missing[0] === "district" ? ["Nashik", "Pune", "Nanded", "Other"] : missing[0] === "land_ownership" ? ["Owner", "Tenant", "Landless"] : missing[0] === "has_bank_account" ? ["Yes", "No"] : ["General", "OBC", "SC", "ST", "Skip"]).map((choice) => <button key={choice} onClick={() => { const field = missing[0]; const next: Partial<Profile> = {}; if (field === "land_acres") next.land_acres = choice.startsWith("Under") ? .5 : choice.startsWith("1") ? 1.5 : choice.startsWith("2") ? 3 : 6; else if (field === "land_ownership") next.land_ownership = choice.toLowerCase() as Profile["land_ownership"]; else if (field === "has_bank_account") next.has_bank_account = choice === "Yes"; else if (field === "category") next.category = choice === "Skip" ? null : choice as Profile["category"]; else next.district = choice; setProfile({ ...profile, ...next }); setMissing(missing.slice(1)); }}>{choice}</button>)}</div><button className="skip" onClick={() => setMissing(missing.slice(1))}>I don&apos;t know yet</button></div>}<ProfileEditor profile={profile} language={language} onChange={(field, value) => setProfile((current) => ({ ...current, [field]: value }))}/><p className="privacy">No identity numbers are collected or required.</p><button className="primary" onClick={confirmProfile} disabled={busy}>{busy ? "Checking…" : t.confirm}<span>→</span></button></section>}

    {screen === "results" && <section className="page"><div className="page-heading"><div><p className="eyebrow">YOUR FARMER SUPPORT LIST</p><h1>{t.results}</h1><p>Based on the details you shared. Review each condition before applying.</p></div><button className="outline" onClick={() => setScreen("profile")}>Edit profile</button></div><div className="result-toolbar">{matches.length} PUBLIC SCHEMES CHECKED <button onClick={openDashboard}>Open tracker ↗</button></div><div className="scheme-grid">{matches.map(renderCard)}</div><p className="disclaimer-banner">{t.estimate}</p></section>}

    {screen === "detail" && selected && <section className="page"><button className="back" onClick={() => setScreen("results")}>← Back to matches</button><div className="page-heading detail-head"><div><span className={`status-pill ${statusClass(selected.status)}`}>{selected.status}</span><h1>{language === "mr" ? selected.scheme.name_mr || selected.scheme.name_en : language === "hi" ? selected.scheme.name_hi || selected.scheme.name_en : selected.scheme.name_en}</h1><p>{selected.scheme.benefit_summary}</p></div><div className="source-box"><b>{selected.scheme.source_name}</b><span>Last verified: {formatDate(selected.scheme.last_verified_date, language)}</span><a href={selected.scheme.official_url} target="_blank" rel="noreferrer">Open official source ↗</a></div></div><p className="disclaimer-banner">{t.estimate}</p><div className="detail-grid"><div><section className="detail-section"><p className="eyebrow">WHY THIS SHOWED UP</p><h2>Your rule check</h2>{selected.reasoning.map((item, index) => <div className="reason-full" key={index}><span className={`reason-dot ${item.result}`}/><b>{fieldLabels[item.field] ?? item.field}</b><span>{item.explanation || item.result}</span><strong>{item.result}</strong></div>)}</section><section className="detail-section"><p className="eyebrow">GET READY</p><h2>{t.documents}</h2>{(selected.scheme.documents ?? []).map((document) => <label className="document" key={document.id}><input type="checkbox" checked={Boolean(readyDocs[document.doc_name_en.toLowerCase()])} onChange={(event) => toggleDocument(document.doc_name_en, event.target.checked)}/><span><b>{document.doc_name_en}</b><small>{document.where_to_get}</small></span></label>)}</section><section className="detail-section"><p className="eyebrow">ONE STEP AT A TIME</p><h2>How to apply</h2><ol className="steps">{(selected.scheme.steps ?? []).map((step) => <li key={step.step_no}><b>{String(step.step_no).padStart(2, "0")}</b><span>{step.text_en}{step.link_nullable && <a href={step.link_nullable} target="_blank" rel="noreferrer">Open link ↗</a>}</span></li>)}</ol></section></div><aside className="apply-box"><p className="eyebrow">READY WHEN YOU ARE</p><h2>Take the next step</h2><p>Visit a Common Service Centre (CSC) or your local Krishi office to apply with help.</p><button className="primary" disabled={busy} onClick={() => startApplication(selected)}>{t.apply}<span>→</span></button></aside></div></section>}

    {screen === "dashboard" && <section className="page"><div className="page-heading"><div><p className="eyebrow">YOUR NEXT STEPS</p><h1>{t.dashboard}</h1></div><span className="notification">♧ {dashboard?.notification_count ?? 0}</span></div>{!dashboard?.applications.length ? <div className="empty"><h2>Your tracker starts here.</h2><p>Find a scheme match and tap “Start application” to add it here.</p><button className="primary" onClick={() => setScreen(matches.length ? "results" : "describe")}>Find a scheme →</button></div> : <><section className="detail-section"><p className="eyebrow">APPLICATION TRACKER</p>{dashboard.applications.map((application) => <div className="tracker" key={application.id}><b>{application.scheme_name}</b><select value={application.status} onChange={async (event) => { await api(`/api/applications/${application.id}`, { method: "PATCH", body: JSON.stringify({ status: event.target.value }) }); openDashboard(); }}>{["Not started", "Documents ready", "Applied", "Under review", "Approved", "Rejected"].map((status) => <option key={status}>{status}</option>)}</select></div>)}</section><div className="dashboard-grid"><section className="detail-section"><p className="eyebrow">DATES TO WATCH</p><h2>Upcoming deadlines</h2>{dashboard.upcoming_deadlines.map((date) => <div className={`deadline ${date.urgent ? "urgent" : ""}`} key={date.scheme_id}><b>{date.scheme_name}</b><span>{date.deadline_date} · {date.days_left} days</span></div>)}</section><section className="detail-section"><p className="eyebrow">GET ONCE, USE AGAIN</p><h2>Document checklist</h2>{dashboard.checklist.map((item) => <label className="document" key={item.doc_name}><input type="checkbox" checked={item.is_ready} onChange={() => toggleDocument(item.doc_name, !item.is_ready)}/><span><b>{item.doc_name}</b><small>{item.where_to_get} · For {item.scheme_count} schemes</small></span></label>)}</section></div></>}<button className="delete-data" onClick={async () => { if (!userId || !confirm("Delete your saved profile and applications?")) return; await api(`/api/users/${userId}`, { method: "DELETE" }); localStorage.removeItem("cwy-user-id"); setUserId(null); setScreen("home"); }}>{t.delete}</button></section>}

    {screen === "outbox" && <section className="page"><p className="eyebrow">DEMO NOTIFICATIONS · MOCK ONLY</p><h1>{t.outbox}</h1><p>Messages are simulated and are never sent to a phone.</p>{messages.length ? messages.map((message) => <article className="message" key={message.id}><b>{message.channel}</b><p>{message.body}</p><small>{message.created_at}</small></article>) : <div className="empty"><h2>No messages yet.</h2><p>Deadline reminders will appear here as simulated messages.</p></div>}</section>}

    {screen === "admin" && <section className="page"><p className="eyebrow">KEEP PUBLIC INFORMATION CURRENT</p><h1>Scheme admin</h1><p>Scheme rules are editable and every change is versioned.</p>{!token ? <form className="admin-login" onSubmit={adminLogin}><label>Email<input type="email" value={adminEmail} onChange={(event) => setAdminEmail(event.target.value)} required/></label><label>Password<input type="password" value={adminPassword} onChange={(event) => setAdminPassword(event.target.value)} required/></label><button className="primary">Sign in →</button></form> : <div className="admin-panel"><b>Authenticated</b><p>{schemes.length} public schemes in the catalogue. Choose the active scheme to add a rule.</p><select id="admin-scheme">{schemes.map((scheme) => <option value={scheme.id} key={scheme.id}>{scheme.name_en}</option>)}</select><form onSubmit={async (event) => { event.preventDefault(); const id = Number((document.getElementById("admin-scheme") as HTMLSelectElement).value); const numeric = ["age", "land_acres", "family_size"].includes(ruleField); await api(`/api/admin/schemes/${id}/rules`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ field: ruleField, operator: "lte", value_json: numeric ? Number(ruleValue) : ruleValue, weight: 1, explanation_en: `${ruleField} is ${ruleValue}` }) }); setError("Rule saved to the audit log."); }}><label>Rule field<select value={ruleField} onChange={(event) => setRuleField(event.target.value)}>{["state", "district", "age", "land_acres", "land_ownership", "income_band", "category", "has_bank_account", "occupation"].map((field) => <option key={field}>{field}</option>)}</select></label><label>Rule value<input value={ruleValue} onChange={(event) => setRuleValue(event.target.value)}/></label><button className="primary">Add rule →</button></form><button className="outline" onClick={async () => { const data = await api("/api/admin/export", { headers: { Authorization: `Bearer ${token}` } }); const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })); link.download = "claim-schemes.json"; link.click(); }}>Export schemes JSON ↓</button><p className="privacy">Verify every rule and source with the official authority before publishing.</p></div>}</section>}

    {screen === "admin" && token && <AdminWorkbench token={token} schemes={adminSchemes} onMessage={setError} onSchemesChange={setAdminSchemes} />}
    {screen === "dashboard" && userId && dashboard?.applications.length ? <form className="reminder-form" onSubmit={savePersonalReminder}><div><p className="eyebrow">YOUR OWN REMINDER</p><strong>Choose a day to check your application</strong></div><input type="date" value={reminderDate} onChange={(event) => setReminderDate(event.target.value)} required/><button className="outline">Save reminder</button></form> : null}

    {screen === "partners" && <section className="page"><p className="eyebrow">A PRACTICAL PARTNERSHIP</p><h1>Local help. Clearer claims.</h1><p>For organisations supporting farming families with public services.</p><div className="impact"><div><b>1,248</b><span>FAMILIES HELPED</span></div><div><b>3,610</b><span>SCHEMES MATCHED</span></div><div><b>642</b><span>APPLICATIONS STARTED</span></div><div><b>218</b><span>COMPLETED</span></div></div><div className="plans">{[["COMMUNITY", "NGO free tier", "Help families with a shared local dashboard."], ["SERVICE CENTRE", "CSC per-seat plan", "Support repeatable applications and progress."], ["CSR PARTNER", "Sponsor reports", "Fund access and receive aggregate impact data."]].map(([type, title, text]) => <article key={type}><small>{type}</small><h2>{title}</h2><p>{text}</p></article>)}</div><p className="privacy">Partner reports use aggregated counts. Personal identity numbers are not collected.</p></section>}

    <footer><span>CLAIM WHAT&apos;S YOURS · PUBLIC INFORMATION ONLY</span><span>VERIFY RULES BEFORE APPLYING</span><button onClick={() => setScreen("partners")}>PARTNER WITH US ↗</button></footer>
  </main>;
}
