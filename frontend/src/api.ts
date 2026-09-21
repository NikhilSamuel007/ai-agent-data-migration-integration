import type { Run, RunSummary, Field, Employee } from "./types";
declare global {
  interface Window {
    RELAY_CONFIG?: { apiBaseUrl: string };
  }
}
const base = (
  window.RELAY_CONFIG?.apiBaseUrl || "http://localhost:8000"
).replace(/\/$/, "");
export const apiUrl = (path: string) => `${base}${path}`;
async function request<T>(path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method: body === undefined ? "GET" : "POST",
      signal: AbortSignal.timeout(30000),
      ...(body === undefined
        ? {}
        : body instanceof FormData
          ? { body }
          : {
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body),
            }),
    });
  } catch {
    throw new Error(
      `Cannot reach the backend at ${base}. Check that the API service is running.`,
    );
  }
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
export const api = {
  runs: () => request<RunSummary[]>("/api/runs"),
  run: (id: string) => request<Run>(`/api/runs/${id}`),
  demo: () => request<Run>("/api/demo", {}),
  upload: (data: FormData) => request<Run>("/api/runs", data),
  mapping: (
    id: string,
    file: string,
    header: string,
    field: Field | null,
    reason: string,
  ) => request(`/api/runs/${id}/mapping`, { file, header, field, reason }),
  resolve: (
    id: string,
    recordId: string,
    action: string,
    data: Partial<Employee>,
    reason: string,
  ) => request(`/api/runs/${id}/records/${recordId}`, { action, data, reason }),
  retry: (id: string) => request(`/api/runs/${id}/retry`, {}),
  rollback: (id: string) => request(`/api/runs/${id}/rollback`, {}),
  schema: () =>
    request<{ fields: Record<string, { type: string; required: boolean; enum?: string[]; description?: string }> }>(
      "/api/schema",
    ),
};
