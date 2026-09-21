export const fieldLabels = {
  employee_id: "Employee ID",
  first_name: "First name",
  last_name: "Last name",
  email: "Work email",
  department: "Department",
  date_of_birth: "Date of birth",
  employment_status: "Employment status",
  account_status: "Account status",
};
export type Field = keyof typeof fieldLabels;
export type Employee = Record<Field, string>;
export interface Issue {
  field: string;
  reason: string;
  choices?: string[];
}
export interface Mapping {
  header: string;
  field: Field | null;
  proposedField?: Field;
  status: string;
  reason: string;
  confidence?: number;
  suggestions: { field: Field; score: number }[];
  evidence?: Record<string, unknown>;
  llmProposal?: {
    target_field: Field;
    confidence: number;
    reason: string;
  } | null;
}
export interface ColumnProfile {
  name: string;
  type: string;
  count: number;
  nonEmpty: number;
  missing: number;
  unique: number;
  samples: string[];
  patterns: Record<string, number>;
}
export interface Source {
  name: string;
  headers: string[];
  rows: Record<string, string>[];
  mapping?: Mapping[];
  profile?: { rowCount: number; columns: ColumnProfile[] };
}
export interface EmployeeRow {
  id: string;
  file: string;
  row: number;
  data: Employee;
  raw: Record<string, string>;
  status: string;
  attempts: number;
  errors: Issue[];
  changes: unknown[];
  integrationError?: string;
  targetId?: string;
  validationAttempts?: number;
}
export interface AuditEvent {
  seq: number;
  at: string;
  action: string;
  detail: Record<string, unknown>;
}
export interface RunSummary {
  id: string;
  name: string;
  status: string;
  createdAt: string;
}
export interface Run extends RunSummary {
  files: Source[];
  records: EmployeeRow[];
  events: AuditEvent[];
  targetCount: number;
  pushStarted: boolean;
  error?: string;
  model: { name: string; status: string };
  llm?: { provider: string; model: string; status: string; error?: string };
}
export type View = "overview" | "review" | "records" | "audit" | "schema";
export const statuses: Record<string, string> = {
  mapping: "Mapping sources",
  mapping_review: "Mapping review",
  cleaning: "Cleaning records",
  review: "Awaiting your review",
  ready: "Ready to integrate",
  pushing: "Integrating",
  partial: "Delivery needs attention",
  complete: "Migration complete",
  rolled_back: "Rolled back",
  error: "Processing failed",
};
export const reviewCount = (r: Run) =>
  r.records.filter((x) => x.status === "review").length +
  r.files.reduce(
    (n, f) =>
      n + (f.mapping || []).filter((m) => m.status === "pending").length,
    0,
  );
