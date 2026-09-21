import type { Run, View } from "../types";
import { reviewCount, statuses } from "../types";
import { ActivityLog, Status, IntegrationActions } from "../components/Shared";
export default function Dashboard({
  run,
  setView,
  act,
  onRollback,
}: {
  run: Run;
  setView: (v: View) => void;
  act: (fn: () => Promise<unknown>) => Promise<void>;
  onRollback: () => void;
}) {
  const count = reviewCount(run);
  return (
    <div className="overview-grid">
      <div>
        <div className="attention">
          <span className="attention-icon">{count ? "◷" : "✓"}</span>
          <div>
            <h3>
              {count
                ? `${count} decision${count === 1 ? " needs" : "s need"} a human perspective`
                : statuses[run.status]}
            </h3>
            <p>
              {count
                ? "Safe decisions are applied. Resolve the remaining uncertainty and the backend will continue automatically."
                : run.status === "partial"
                  ? "Automatic retries are exhausted for some records. Review the failure and retry or roll back."
                  : run.error ||
                    "Every source row, transformation, and target write remains traceable."}
            </p>
            {count > 0 && (
              <button
                className="button primary"
                onClick={() => setView("review")}
              >
                Review decisions →
              </button>
            )}
            <IntegrationActions {...{ run, act, onRollback }} />
          </div>
        </div>
        <section className="card">
          <div className="card-head">
            <h3>Source files</h3>
            <small>{run.files.length} files connected</small>
          </div>
          {run.files.map((f) => (
            <div className="source" key={f.name}>
              <span className="file-icon">
                {f.name.endsWith(".xlsx") ? "XLSX" : "CSV"}
              </span>
              <div>
                <strong>{f.name}</strong>
                <small>
                  {f.rows.length} records · {f.headers.length} columns
                </small>
              </div>
              <Status
                value={
                  f.mapping?.some((m) => m.status === "pending")
                    ? "review"
                    : f.mapping
                      ? "mapped"
                      : "analyzing"
                }
              />
            </div>
          ))}
        </section>
        <section className="card">
          <div className="card-head">
            <h3>Mapping decisions</h3>
            <small>Evidence, not model authority</small>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Target</th>
                  <th>Decision</th>
                  <th>Policy score</th>
                </tr>
              </thead>
              <tbody>
                {run.files.flatMap((f) =>
                  (f.mapping || []).map((m) => (
                    <tr key={`${f.name}:${m.header}`}>
                      <td>
                        {m.header}
                        <small>{f.name}</small>
                      </td>
                      <td>{m.field || m.proposedField || "Unassigned"}</td>
                      <td>
                        <Status value={m.status} />
                      </td>
                      <td>
                        {m.evidence?.alias
                          ? "Explicit alias"
                          : m.confidence === undefined
                            ? "—"
                            : m.confidence.toFixed(2)}
                      </td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
        </section>
        <section className="card">
          <div className="card-head">
            <h3>Source profiles</h3>
            <small>Measured before mapping</small>
          </div>
          {run.files.map((f) => (
            <details className="audit-row" key={f.name}>
              <summary>
                <strong>{f.name}</strong>
                <small>{f.profile?.rowCount ?? f.rows.length} rows</small>
              </summary>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Column</th>
                      <th>Type</th>
                      <th>Missing</th>
                      <th>Unique</th>
                      <th>Samples</th>
                    </tr>
                  </thead>
                  <tbody>
                    {f.profile?.columns.map((p) => (
                      <tr key={p.name}>
                        <td>{p.name}</td>
                        <td>{p.type}</td>
                        <td>{p.missing}</td>
                        <td>{p.unique}</td>
                        <td>{p.samples.join(" / ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!f.profile && (
                <p>
                  Profile unavailable for a migration created before profiling
                  was added.
                </p>
              )}
            </details>
          ))}
        </section>
      </div>
      <div>
        <section className="card">
          <div className="card-head">
            <h3>Agent guardrails</h3>
            <Status value="active" />
          </div>
          <div className="card-body">
            {[
              [
                "✓",
                "Handle the predictable",
                "Explicit aliases, whitespace, email casing, and unambiguous dates.",
              ],
              [
                "⊙",
                "Require corroborating evidence",
                "Semantic mappings need model agreement, compatible values, a clear margin, and sufficient samples.",
              ],
              [
                "↶",
                "Recover without guessing",
                "Retry transient errors up to three times. Escalate conflicts and exhausted retries.",
              ],
            ].map(([icon, title, text]) => (
              <div className="policy-row" key={title}>
                <span>{icon}</span>
                <div>
                  <strong>{title}</strong>
                  <p>{text}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="model-note">
            <strong>Ollama · {run.llm?.model || "qwen2.5:1.5b"}</strong>
            <br />
            {run.llm?.status || "not used"}
            {run.llm?.status === "unavailable" && (
              <p>
                LLM unavailable. Semantic suggestions remain available, but
                require human review.
              </p>
            )}
            <br />
            MiniLM semantic model: {run.model.status}
          </div>
        </section>
        <section className="card">
          <div className="card-head">
            <h3>Live activity</h3>
            <button className="text-button" onClick={() => setView("audit")}>
              View all →
            </button>
          </div>
          <ActivityLog events={run.events} />
        </section>
      </div>
    </div>
  );
}
