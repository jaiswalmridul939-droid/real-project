export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Profile = {
  state?: string | null;
  district?: string | null;
  age?: number | null;
  gender?: string | null;
  land_acres?: number | null;
  land_ownership?: "owner" | "tenant" | "landless" | null;
  income_band?: string | null;
  category?: "General" | "OBC" | "SC" | "ST" | null;
  has_bank_account?: boolean | null;
  is_woman?: boolean | null;
  crops?: string[] | null;
  family_size?: number | null;
  occupation?: string | null;
};

export type Scheme = {
  id: number;
  name_en: string;
  name_mr: string;
  name_hi: string;
  description_en: string;
  department: string;
  level: string;
  benefit_summary: string;
  official_url: string;
  source_name: string;
  last_verified_date: string;
  is_outdated?: boolean;
  deadline_date: string | null;
  is_active: boolean;
  version: number;
  rules?: { id: number; field: string; operator: string; value_json: unknown; explanation_en: string }[];
  documents?: { id: number; doc_name_en: string; where_to_get: string; is_mandatory: boolean }[];
  steps?: { id: number; step_no: number; text_en: string; link_nullable: string | null }[];
};

export type Match = {
  scheme: Scheme;
  status: string;
  reasoning: { field: string; operator: string; expected: unknown; actual: unknown; result: string; explanation: string }[];
  disclaimer: string;
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}