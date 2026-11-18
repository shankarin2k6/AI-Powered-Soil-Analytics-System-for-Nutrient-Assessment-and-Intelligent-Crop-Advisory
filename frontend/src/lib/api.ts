/** The only file that talks to the backend. Every page uses these functions. */

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const V1 = `${API_URL}/api/v1`;

export class ApiError extends Error {
  constructor(public status: number, message: string, public messageKey?: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    // credentials: "include" sends the login cookie to the API (which runs on another port)
    res = await fetch(`${V1}${path}`, { ...init, credentials: "include" });
  } catch {
    throw new ApiError(0, "Network error", "error.network");
  }
  if (!res.ok) {
    // the login expired while the app was open: AuthProvider listens and shows the login page
    if (res.status === 401 && !path.startsWith("/auth/")) window.dispatchEvent(new Event("auth:expired"));
    let detail: unknown;
    let key: string | undefined;
    try {
      const body = await res.json();
      detail = body.detail;
      key = body.message_key;
    } catch {
      /* the body was not JSON */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : "Request failed", key);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

// ---- types (they mirror backend/app/schemas) ----
export type Farmer = {
  id: number; name: string; phone: string | null; language: string;
  email?: string | null; address?: string | null;   // optional profile details
};
export type ProfileInput = { name: string; phone: string; email: string; address: string };
export type Field = { id: number; farmer_id: number; name: string };
export type ImageRecord = {
  id: number;
  field_id: number;
  width: number;
  height: number;
  quality: { blur_score: number; brightness: number; warnings: string[] };
  urls: Record<string, string>;
  created_at: string;
};
export type SoilTestInput = {
  nitrogen: number;
  phosphorus: number;
  potassium: number;
  ph: number;
  organic_matter?: number;
  moisture?: number;
  tested_on?: string;
  image_id?: number;
};
export type SoilTestRecord = Required<Pick<SoilTestInput, "nitrogen" | "phosphorus" | "potassium" | "ph">> & {
  id: number;
  organic_matter: number | null;
  moisture: number | null;
  tested_on: string | null;
  image_id: number | null;
  created_at: string;
};

// ---- analysis (Milestone 2); mirrors the `result` JSON built in backend/app/api/analysis.py ----
export type Level = "low" | "medium" | "high";
export type Unavailable = { available: false; reason_key: string };
export type SoilCandidate = { soil_class: string; probability: number };
export type ImageResult =
  | Unavailable
  | {
      available: true;
      tier: "confident" | "confirm" | "retake" | "not_soil";
      soil_class: string | null;
      confidence: number;
      candidates: SoilCandidate[];
      top3: SoilCandidate[];
      message_key: string;
      has_gradcam?: boolean;
    };
export type LabRating = { parameter: string; value: number; unit: string; level: string; score: number; message_key: string };
export type Deficiency = { nutrient: string; value: number; unit: string; support: ("lab" | "model")[]; message_key: string };
export type ShapFeature = { feature: string; contribution: number; direction: "towards" | "away" };
export type FertilizerSignal =
  | { available: false; reason_key: string; missing?: string[] }
  | {
      available: true;
      confident: boolean;
      recommendations: { label: string; probability: number }[];
      notes: string[];
      explanation: { for: string; method: string; features: ShapFeature[] };
      inputs_used: { soil_type: string; assumed_defaults: string[] };
    };
export type CropMatch = {
  crop: string; score: number; fit: "very_suitable" | "suitable" | "possible"; message_key: string; reasons: { key: string }[];
};
export type CropRanking =
  | { available: false; reason_key: string }
  | { available: true; soil_class: string | null; top: CropMatch[]; summary_key: string };
export type PlanItem = { product: "urea" | "dap" | "mop" | "fym" | "lime" | "gypsum"; kg: number };
export type PlanStep = {
  id: string; day: number | null; title_key: string; title_params?: Record<string, number>;
  timing_key: string; timing_params?: Record<string, number>; how_key: string; items: PlanItem[];
  state: "past" | "now" | "later" | null;
};
export type FertilizerPlan =
  | { available: false; reason_key: string }
  | { available: true; crop: string; stage: string; unit: "acre";
      nutrients: { n: number; p2o5: number; k2o: number };
      adjustments: { nutrient: "nitrogen" | "phosphorus" | "potassium"; level: "low" | "medium" | "high" | "unknown"; factor: number }[];
      steps: PlanStep[]; shopping: PlanItem[]; notes: string[] };
export type Trend = {
  points: { analysis_id: number; date: string; health_score: number; degradation_index: number | null }[];
  enough_data: boolean; direction: "improving" | "steady" | "declining" | null;
  change_per_month: number | null; estimate_90d: number | null; message_key: string;
};
export type AnalysisResult = {
  inputs: { image_id: number | null; soil_test_id: number | null };
  image: ImageResult;
  lab: { values: Record<string, number | string | null>; ratings: LabRating[] } | null;
  fusion: { soil_class: string | null; soil_class_source: "image" | "user" | null; lab_hint?: string | null; notes: string[] };
  fertilizer_signal: FertilizerSignal;
  health: { score: number; grade: "good" | "moderate" | "poor"; message_key: string;
            components: { parameter: string; score: number; weight: number }[] } | null;
  degradation: { index: number; level: "low" | "moderate" | "high"; message_key: string;
                 drivers: { factor: string; share: number; message_key: string }[] } | null;
  diagnosis: { deficiencies: Deficiency[]; ph_issue: { level: string; value: number; message_key: string } | null; summary_key: string };
  crops?: CropRanking;     // missing on analyses saved before Milestone 3
  warnings: { key: string; source?: string }[];
};
export type AnalysisRecord = {
  id: number; field_id: number; image_id: number | null; soil_test_id: number | null;
  model_version: string | null; created_at: string; result: AnalysisResult;
};
export type AnalyzeInput = {
  image_id?: number; soil_test_id?: number; confirmed_soil_class?: string;
  crop_type?: string; growth_stage?: string; season?: string;
};
export type ModelStatus = {
  image_model: boolean; fertilizer_model: boolean; classes: string[];
  fertilizer_options: { crop_type?: string[]; growth_stage?: string[]; season?: string[] };
};

export type HistoryItem =
  | { type: "image"; id: number; created_at: string; data: ImageRecord }
  | { type: "soil_test"; id: number; created_at: string; data: SoilTestRecord }
  | { type: "analysis"; id: number; created_at: string; data: { image_id: number | null; soil_test_id: number | null; model_version: string | null; result: AnalysisResult } };

// ---- calls ----
export const api = {
  // accounts
  signup: (name: string, phone: string, password: string, language: string) =>
    request<Farmer>("/auth/signup", json({ name, phone, password, language })),
  setLanguage: (language: string) => request<Farmer>("/auth/me/language", json({ language }, "PUT")),
  login: (phone: string, password: string) => request<Farmer>("/auth/login", json({ phone, password })),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  me: () => request<Farmer>("/auth/me"),
  updateProfile: (body: ProfileInput) => request<Farmer>("/auth/me", json(body, "PATCH")),

  // fields
  listFields: () => request<Field[]>("/fields"),
  createField: (name: string) => request<Field>("/fields", json({ name })),

  // data
  uploadImage(fieldId: number, photo: Blob) {
    const form = new FormData();
    form.append("file", photo, "soil.jpg");
    return request<ImageRecord>(`/fields/${fieldId}/images`, { method: "POST", body: form });
  },
  createSoilTest: (fieldId: number, body: SoilTestInput) =>
    request<SoilTestRecord>(`/fields/${fieldId}/soil-tests`, json(body)),
  listImages: (fieldId: number) => request<ImageRecord[]>(`/fields/${fieldId}/images`),
  updateSoilTest: (id: number, body: Omit<SoilTestInput, "image_id">) =>
    request<SoilTestRecord>(`/soil-tests/${id}`, json(body, "PUT")),
  listSoilTests: (fieldId: number) => request<SoilTestRecord[]>(`/fields/${fieldId}/soil-tests`),
  planCrops: () => request<{ crops: string[]; stages: string[] }>("/fertilizer-plan/crops"),
  fertilizerPlan: (analysisId: number, crop: string, stage: string) =>
    request<FertilizerPlan>(`/analyses/${analysisId}/fertilizer-plan?crop=${encodeURIComponent(crop)}&stage=${encodeURIComponent(stage)}`),
  voiceStatus: () => request<{ enabled: boolean }>("/voice/status"),
  /** Spoken version of a text (Sarvam AI through our server). Returns an audio Blob. */
  speak: async (text: string, language: string): Promise<Blob> => {
    let res: Response;
    try {
      res = await fetch(`${V1}/voice/speak`, { ...json({ text, language }), credentials: "include" });
    } catch {
      throw new ApiError(0, "Network error", "error.network");
    }
    if (!res.ok) {
      let key: string | undefined;
      try { key = (await res.json()).message_key; } catch { /* not JSON */ }
      throw new ApiError(res.status, "Voice failed", key ?? "voice.error");
    }
    return res.blob();
  },
  trend: (fieldId: number) => request<Trend>(`/fields/${fieldId}/trend`),
  history: (fieldId: number) => request<HistoryItem[]>(`/fields/${fieldId}/history`),

  // analysis (Milestone 2)
  analyze: (fieldId: number, body: AnalyzeInput) => request<AnalysisRecord>(`/fields/${fieldId}/analyze`, json(body)),
  getAnalysis: (id: number) => request<AnalysisRecord>(`/analyses/${id}`),
  modelStatus: () => request<ModelStatus>("/analysis/status"),
};

/** Address of the Grad-CAM heat-map picture of a saved analysis. */
export const gradcamUrl = (analysisId: number) => `${V1}/analyses/${analysisId}/gradcam`;

/** Turns a path returned by the API (for example urls.normalized) into a full address for <img src>. */
export const mediaUrl = (path: string) => `${API_URL}${path}`;
