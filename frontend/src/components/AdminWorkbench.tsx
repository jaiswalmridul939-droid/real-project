"use client";

import { FormEvent, useState } from "react";
import { api, Scheme } from "@/lib/api";

type AuditEntry = { id: number; scheme_id: number | null; changed_by: string; change_json: { action?: string }; created_at: string | null };

export function AdminWorkbench({ token, schemes, onMessage, onSchemesChange }: { token: string; schemes: Scheme[]; onMessage: (message: string) => void; onSchemesChange?: (schemes: Scheme[]) => void }) {
  const [currentSchemes, setCurrentSchemes] = useState(schemes);
  const [schemeId, setSchemeId] = useState<number | null>(null);
  const [documentName, setDocumentName] = useState("");
  const [documentSource, setDocumentSource] = useState("");
  const [documentId, setDocumentId] = useState<number | null>(null);
  const [stepText, setStepText] = useState("");
  const [stepLink, setStepLink] = useState("");
  const [stepId, setStepId] = useState<number | null>(null);
  const [stepNumber, setStepNumber] = useState(1);
  const [ruleId, setRuleId] = useState<number | null>(null);
  const [ruleField, setRuleField] = useState("land_acres");
  const [ruleOperator, setRuleOperator] = useState("lte");
  const [ruleValue, setRuleValue] = useState("5");
  const [ruleExplanation, setRuleExplanation] = useState("");
  const [newSchemeName, setNewSchemeName] = useState("");
  const [newSchemeUrl, setNewSchemeUrl] = useState("");
  const [newSchemeSource, setNewSchemeSource] = useState("");
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const selected = currentSchemes.find((scheme) => scheme.id === (schemeId ?? currentSchemes[0]?.id));
  const headers = { Authorization: `Bearer ${token}` };

  async function refreshSchemes() {
    const refreshed = await api<Scheme[]>("/api/admin/schemes", { headers });
    setCurrentSchemes(refreshed);
    onSchemesChange?.(refreshed);
  }

  function ruleValueJson() {
    if (["age", "land_acres", "family_size"].includes(ruleField)) return Number(ruleValue);
    if (ruleOperator === "in") return ruleValue.split(",").map((value) => value.trim());
    if (ruleField === "has_bank_account" || ruleField === "is_woman") return ruleValue.toLowerCase() === "true";
    return ruleValue;
  }

  async function saveRule(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    const body = JSON.stringify({ field: ruleField, operator: ruleOperator, value_json: ruleValueJson(), weight: 1, explanation_en: ruleExplanation });
    await api(ruleId ? `/api/admin/rules/${ruleId}` : `/api/admin/schemes/${selected.id}/rules`, { method: ruleId ? "PUT" : "POST", headers, body });
    setRuleId(null); setRuleExplanation(""); onMessage("Rule saved and audited."); await refreshSchemes();
  }

  async function removeRule(id: number) {
    await api(`/api/admin/rules/${id}`, { method: "DELETE", headers });
    onMessage("Rule deleted and audited."); await refreshSchemes();
  }

  async function saveDocument(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    const body = JSON.stringify({ doc_name_en: documentName, where_to_get: documentSource, is_mandatory: true });
    await api(documentId ? `/api/admin/documents/${documentId}` : `/api/admin/schemes/${selected.id}/documents`, { method: documentId ? "PUT" : "POST", headers, body });
    setDocumentId(null); setDocumentName(""); setDocumentSource(""); onMessage("Document saved and audited."); await refreshSchemes();
  }

  async function removeDocument(id: number) {
    await api(`/api/admin/documents/${id}`, { method: "DELETE", headers });
    onMessage("Document deleted and audited."); await refreshSchemes();
  }

  async function saveStep(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    const body = JSON.stringify({ step_no: stepNumber, text_en: stepText, link_nullable: stepLink || null });
    await api(stepId ? `/api/admin/steps/${stepId}` : `/api/admin/schemes/${selected.id}/steps`, { method: stepId ? "PUT" : "POST", headers, body });
    setStepId(null); setStepText(""); setStepLink(""); setStepNumber((selected.steps?.length ?? 0) + 2); onMessage("Application step saved and audited."); await refreshSchemes();
  }

  async function removeStep(id: number) {
    await api(`/api/admin/steps/${id}`, { method: "DELETE", headers });
    onMessage("Step deleted and audited."); await refreshSchemes();
  }

  async function updateVerification(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    const formData = new FormData(event.currentTarget as HTMLFormElement);
    await api(`/api/admin/schemes/${selected.id}`, { method: "PUT", headers, body: JSON.stringify({ ...selected, name_en: formData.get("edit-name"), official_url: formData.get("edit-url"), source_name: formData.get("edit-source"), last_verified_date: formData.get("edit-verified"), deadline_date: formData.get("edit-deadline") || null }) });
    onMessage("Scheme details updated and audited."); await refreshSchemes();
  }

  async function createScheme(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const data = new FormData(form);
    await api("/api/admin/schemes", { method: "POST", headers, body: JSON.stringify({ name_en: newSchemeName, official_url: newSchemeUrl, source_name: newSchemeSource, last_verified_date: data.get("new-verified"), benefit_summary: "Check the official source for current benefits.", description_en: "Public scheme information. Verify current requirements before applying.", department: "", level: "central", is_active: true }) });
    setNewSchemeName(""); setNewSchemeUrl(""); setNewSchemeSource(""); onMessage("Scheme added and recorded in the audit log."); await refreshSchemes();
  }

  async function disableScheme() {
    if (!selected || !window.confirm(`Disable ${selected.name_en}?`)) return;
    await api(`/api/admin/schemes/${selected.id}`, { method: "DELETE", headers });
    onMessage("Scheme disabled and logged."); await refreshSchemes();
  }

  async function exportData() {
    const data = await api("/api/admin/export", { headers });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    link.download = "claim-schemes.json"; link.click(); URL.revokeObjectURL(link.href);
  }

  async function importData(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = (event.currentTarget.elements.namedItem("scheme-import") as HTMLInputElement).files?.[0];
    if (!file) return;
    const result = await api<{ imported: number }>("/api/admin/import", { method: "POST", headers, body: JSON.stringify(JSON.parse(await file.text())) });
    onMessage(`${result.imported} schemes imported and audited.`); await refreshSchemes();
  }

  async function loadAudit() {
    setAudit(await api<AuditEntry[]>("/api/admin/audit", { headers }));
  }

  return <section className="workbench">
    <div className="workbench-heading"><div><p className="eyebrow">SCHEME CONTENT</p><h2>Maintain the public record</h2></div><select aria-label="Select scheme" value={selected?.id ?? ""} onChange={(event) => setSchemeId(Number(event.target.value))}>{currentSchemes.map((scheme) => <option value={scheme.id} key={scheme.id}>{scheme.name_en}</option>)}</select></div>
    <form className="new-scheme-form" onSubmit={createScheme}><p className="eyebrow">ADD SCHEME</p><label>English name<input value={newSchemeName} onChange={(event) => setNewSchemeName(event.target.value)} required /></label><label>Official URL<input type="url" value={newSchemeUrl} onChange={(event) => setNewSchemeUrl(event.target.value)} required /></label><label>Source name<input value={newSchemeSource} onChange={(event) => setNewSchemeSource(event.target.value)} required /></label><label>Last verified<input type="date" name="new-verified" required /></label><button className="outline">Add scheme</button></form>
    {selected && <div className="workbench-grid">
      <form className="workbench-card" key={selected.id} onSubmit={updateVerification}><p className="eyebrow">SCHEME RECORD · VERSION {selected.version}</p><h3>Edit scheme details</h3><label>English name<input name="edit-name" defaultValue={selected.name_en} required /></label><label>Official URL<input name="edit-url" type="url" defaultValue={selected.official_url} required /></label><label>Source name<input name="edit-source" defaultValue={selected.source_name} required /></label><label>Last verified<input name="edit-verified" type="date" defaultValue={selected.last_verified_date} required /></label><label>Deadline (optional)<input name="edit-deadline" type="date" defaultValue={selected.deadline_date ?? ""} /></label><button className="outline">Save scheme details</button><button type="button" className="danger-button" onClick={disableScheme}>Disable scheme</button><a href={selected.official_url} target="_blank" rel="noreferrer">{selected.source_name} ↗</a></form>
      <section className="workbench-card"><p className="eyebrow">RULE BUILDER</p><h3>{ruleId ? "Edit rule" : "Add a rule"}</h3><form onSubmit={saveRule}><label>Field<select value={ruleField} onChange={(event) => setRuleField(event.target.value)}>{["state", "district", "age", "land_acres", "land_ownership", "income_band", "category", "has_bank_account", "is_woman", "crops", "family_size", "occupation"].map((field) => <option key={field}>{field}</option>)}</select></label><label>Operator<select value={ruleOperator} onChange={(event) => setRuleOperator(event.target.value)}>{["eq", "neq", "lt", "lte", "gt", "gte", "contains", "in", "exists"].map((operator) => <option key={operator}>{operator}</option>)}</select></label><label>Value<input value={ruleValue} onChange={(event) => setRuleValue(event.target.value)} required /></label><label>Reason shown to families<input value={ruleExplanation} onChange={(event) => setRuleExplanation(event.target.value)} /></label><button className="outline">{ruleId ? "Save rule" : "Add rule"}</button></form>{(selected.rules ?? []).map((rule) => <div className="editable-row" key={rule.id}><span><b>{rule.field} {rule.operator} {JSON.stringify(rule.value_json)}</b><small>{rule.explanation_en}</small></span><button onClick={() => { setRuleId(rule.id); setRuleField(rule.field); setRuleOperator(rule.operator); setRuleValue(Array.isArray(rule.value_json) ? rule.value_json.join(", ") : String(rule.value_json)); setRuleExplanation(rule.explanation_en); }}>Edit</button><button onClick={() => removeRule(rule.id)}>Delete</button></div>)}</section>
      <section className="workbench-card"><p className="eyebrow">DOCUMENT CHECKLIST</p><h3>{documentId ? "Edit document" : "Add a document"}</h3><form onSubmit={saveDocument}><label>Document name<input value={documentName} onChange={(event) => setDocumentName(event.target.value)} required /></label><label>Where to get it<input value={documentSource} onChange={(event) => setDocumentSource(event.target.value)} required /></label><button className="outline">{documentId ? "Save document" : "Add required document"}</button></form>{(selected.documents ?? []).map((document) => <div className="editable-row" key={document.id}><span><b>{document.doc_name_en}</b><small>{document.where_to_get}</small></span><button onClick={() => { setDocumentId(document.id); setDocumentName(document.doc_name_en); setDocumentSource(document.where_to_get); }}>Edit</button><button onClick={() => removeDocument(document.id)}>Delete</button></div>)}</section>
      <section className="workbench-card"><p className="eyebrow">APPLICATION GUIDE</p><h3>{stepId ? "Edit step" : "Add an apply step"}</h3><form onSubmit={saveStep}><label>Step number<input type="number" min="1" value={stepNumber} onChange={(event) => setStepNumber(Number(event.target.value))} required /></label><label>Step instruction<input value={stepText} onChange={(event) => setStepText(event.target.value)} required /></label><label>Official link<input type="url" value={stepLink} onChange={(event) => setStepLink(event.target.value)} /></label><button className="outline">{stepId ? "Save step" : "Add numbered step"}</button></form>{(selected.steps ?? []).map((step) => <div className="editable-row" key={step.id}><span><b>{step.step_no}. {step.text_en}</b><small>{step.link_nullable}</small></span><button onClick={() => { setStepId(step.id); setStepNumber(step.step_no); setStepText(step.text_en); setStepLink(step.link_nullable ?? ""); }}>Edit</button><button onClick={() => removeStep(step.id)}>Delete</button></div>)}</section>
      <div className="workbench-card"><p className="eyebrow">BACKUP AND HISTORY</p><h3>Rules change. Keep a record.</h3><div className="workbench-actions"><button className="outline" onClick={exportData}>Export JSON ↓</button><form onSubmit={importData}><input type="file" name="scheme-import" accept="application/json" required /><button className="outline">Import JSON ↑</button></form><button className="outline" onClick={loadAudit}>Refresh audit log ↻</button></div>{audit.map((entry) => <div className="audit-entry" key={entry.id}><b>{entry.change_json.action ?? "change"}</b><span>{entry.changed_by}</span><small>{entry.created_at ?? "just now"}</small></div>)}</div>
    </div>}
  </section>;
}