import type {
  ActivityPayload,
  ContextPayload,
  HistoryPayload,
  InvestigationDetail,
  InvestigationExplorerPayload,
  ManifestPayload,
  MethodologyPayload,
  OverviewPayload,
  ReactionValidationPayload,
  SummaryPayload
} from "../types";

const BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `SIGNAL API ${response.status}: ${text || response.statusText}`
    );
  }

  return response.json() as Promise<T>;
}

export function getManifest() {
  return getJson<ManifestPayload>("/api/manifest");
}

export function getOverview() {
  return getJson<OverviewPayload>("/api/overview");
}

export interface InvestigationQuery {
  state?: string;
  peer_group?: string;
  context_scope?: string;
  active?: boolean;
  q?: string;
}

export function getInvestigations(query: InvestigationQuery = {}) {
  const params = new URLSearchParams();

  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  });

  const suffix = params.toString() ? `?${params.toString()}` : "";

  return getJson<InvestigationExplorerPayload>(
    `/api/investigations${suffix}`
  );
}

export function getInvestigation(symbol: string) {
  return getJson<InvestigationDetail>(
    `/api/investigations/${encodeURIComponent(symbol)}`
  );
}

export function getSummary(symbol: string) {
  return getJson<SummaryPayload>(
    `/api/investigations/${encodeURIComponent(symbol)}/summary`
  );
}

export function getActivity(symbol: string) {
  return getJson<ActivityPayload>(
    `/api/investigations/${encodeURIComponent(symbol)}/activity`
  );
}

export function getContext(symbol: string) {
  return getJson<ContextPayload>(
    `/api/investigations/${encodeURIComponent(symbol)}/context`
  );
}

export function getHistory(symbol: string) {
  return getJson<HistoryPayload>(
    `/api/investigations/${encodeURIComponent(symbol)}/history`
  );
}

export function getMethodology() {
  return getJson<MethodologyPayload>("/api/methodology");
}


export function getReactionValidation() {
  return getJson<ReactionValidationPayload>("/api/reaction-validation");
}
