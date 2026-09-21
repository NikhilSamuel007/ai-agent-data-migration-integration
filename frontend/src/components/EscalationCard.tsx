import { useState } from "react";
import { api } from "../api";
import type {
  Run,
  Source,
  Mapping,
  Field,
  EmployeeRow,
  Employee,
} from "../types";
import { fieldLabels } from "../types";
type Action = (fn: () => Promise<unknown>) => Promise<void>;
export function MappingCard({
  run,
  file,
  mapping,
  act,
}: {
  run: Run;
  file: Source;
  mapping: Mapping;
  act: Action;
}) {
  const [field, setField] = useState(""),
    [reason, setReason] = useState("");
  const profile = file.profile?.columns.find((p) => p.name === mapping.header);
  return (
    <form
      className="review-card mapping-form"
      data-header={mapping.header}
      onSubmit={(e) => {
        e.preventDefault();
        if (field)
          void act(() =>
            api.mapping(
              run.id,
              file.name,
              mapping.header,
              field === "__ignore" ? null : (field as Field),
              reason,
            ),
          );
      }}
    >
      <span className="section-kicker">COLUMN MAPPING · {file.name}</span>
      <h3>Where does “{mapping.header}” belong?</h3>
      <p>
        Samples:{" "}
        {(
          profile?.samples ||
          file.rows.slice(0, 3).map((r) => r[mapping.header])
        ).join(" / ")}
      </p>
      <div className="issue">
        {mapping.reason}
        <br />
        Policy score: {mapping.confidence?.toFixed(2) ?? "—"} / 1.00 — not a
        calibrated probability.
      </div>
      <p>
        Model suggestions:{" "}
        {mapping.suggestions
          .map((s) => `${fieldLabels[s.field]} (${s.score.toFixed(2)})`)
          .join(" · ") || "Unavailable"}
      </p>
      {mapping.llmProposal && (
        <p>
          Ollama: {fieldLabels[mapping.llmProposal.target_field]} —{" "}
          {mapping.llmProposal.reason}
        </p>
      )}
      <details className="raw">
        <summary>Why the agent escalated</summary>
        <pre>{JSON.stringify(mapping.evidence || {}, null, 2)}</pre>
      </details>
      <div className="mapping-grid">
        <label>
          Target field
          <select
            required
            value={field}
            onChange={(e) => setField(e.target.value)}
          >
            <option value="">Choose a field</option>
            {Object.entries(fieldLabels)
              .filter(([k]) => !file.mapping?.some((m) => m.field === k))
              .map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            <option value="__ignore">Ignore this source column</option>
          </select>
        </label>
        <label>
          Decision note
          <input
            name="reason"
            required
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
      </div>
      <button className="button primary">Approve mapping</button>
    </form>
  );
}
export function RecordCard({
  run,
  row,
  act,
}: {
  run: Run;
  row: EmployeeRow;
  act: Action;
}) {
  const [data, setData] = useState<Employee>({ ...row.data }),
    [reason, setReason] = useState("");
  return (
    <form
      className="review-card record-form"
      onSubmit={(e) => {
        e.preventDefault();
        const action =
          (e.nativeEvent as SubmitEvent).submitter?.getAttribute("value") ||
          "correct";
        void act(() => api.resolve(run.id, row.id, action, data, reason));
      }}
    >
      <span className="section-kicker">
        RECORD REVIEW · {row.file} : ROW {row.row}
      </span>
      <h3>{[row.data.first_name, row.data.last_name].filter(Boolean).join(" ") || "Unnamed employee"}</h3>
      <p>
        {row.data.email} · {row.data.department}
      </p>
      <div className="issue">
        {row.errors.map((error, i) => (
          <div key={i}>
            <strong>
              {fieldLabels[error.field as Field] || "Identity conflict"}:
            </strong>{" "}
            {error.reason}
          </div>
        ))}
      </div>
      <div className="choices">
        {row.errors
          .flatMap((e) => e.choices || [])
          .map((date) => (
            <button
              key={date}
              className="choice"
              type="button"
              onClick={() => setData({ ...data, date_of_birth: date })}
            >
              Use {date}
            </button>
          ))}
      </div>
      <div className="review-fields">
        {Object.entries(fieldLabels).map(([key, label]) => (
          <label key={key}>
            {label}
            <input
              name={key}
              value={data[key as Field]}
              required={["employee_id", "first_name", "last_name", "email", "date_of_birth", "employment_status"].includes(key)}
              onChange={(e) => setData({ ...data, [key]: e.target.value })}
            />
          </label>
        ))}
      </div>
      <details className="raw">
        <summary>Original source row & safe changes</summary>
        <pre>
          {JSON.stringify(
            {
              source: row.raw,
              changes: row.changes,
              validationAttempts: row.validationAttempts,
            },
            null,
            2,
          )}
        </pre>
      </details>
      <div className="review-actions">
        <input
          aria-label="Decision note"
          placeholder="Decision note"
          required
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        <button className="button primary" value="correct">
          Save correction
        </button>
        <button className="button secondary" value="approve">
          Approve as entered
        </button>
        <button
          className="text-button reject"
          type="button"
          onClick={() => {
            if (reason.trim())
              void act(() => api.resolve(run.id, row.id, "reject", {}, reason));
          }}
          disabled={!reason.trim()}
        >
          Reject record
        </button>
      </div>
    </form>
  );
}
