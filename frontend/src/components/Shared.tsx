import type { Run, AuditEvent } from "../types";
import { statuses, reviewCount } from "../types";
import { api } from "../api";
export function Status({ value, id }: { value: string; id?: string }) {
  return (
    <span
      id={id}
      className={`pill ${["review", "mapping_review", "partial", "failed"].includes(value) ? "warning" : value === "error" ? "error" : ""}`}
    >
      {statuses[value] || value.replaceAll("_", " ")}
    </span>
  );
}
export function MigrationStats({ run }: { run: Run }) {
  const source = run.files.reduce((n, f) => n + f.rows.length, 0);
  const ready = run.records.filter((r) =>
    ["ready", "pushed", "failed", "sending"].includes(r.status),
  ).length;
  return (
    <>
      <section className="stats">
        <div>
          <span>Source records</span>
          <strong id="stat-source">{source}</strong>
          <small>{run.files.length} source files</small>
        </div>
        <div>
          <span>Ready for target</span>
          <strong id="stat-ready">{ready}</strong>
          <small>Validated & reconciled</small>
        </div>
        <div className="review-stat">
          <span>Need your judgment</span>
          <strong id="stat-review">{reviewCount(run)}</strong>
          <small>Only unresolved cases</small>
        </div>
        <div>
          <span>Delivered to target</span>
          <strong id="stat-pushed">{run.targetCount}</strong>
          <small>
            {run.records.filter((r) => r.status === "failed").length} failed ·{" "}
            {run.records.filter((r) => r.status === "duplicate").length}{" "}
            duplicates
          </small>
        </div>
      </section>
      <section className="pipeline" aria-label="Migration stages">
        {["Ingest & profile", "Map & clean", "Review", "Integrate"].map(
          (stage, i) => (
            <div
              key={stage}
              className={
                i === 0 || run.status === "complete"
                  ? "done"
                  : i === 2 && reviewCount(run) > 0
                    ? "current"
                    : ""
              }
            >
              <span>{i + 1}</span>
              <div>{stage}</div>
              {i < 3 && <i />}
            </div>
          ),
        )}
      </section>
    </>
  );
}
export function ActivityLog({ events }: { events: AuditEvent[] }) {
  return (
    <div className="card-body">
      {events.slice(0, 6).map((e) => (
        <div className="timeline-item" key={e.seq}>
          <strong>{e.action}</strong>
          <p>
            {String(
              e.detail.reason ||
                e.detail.file ||
                e.detail.email ||
                "Decision saved to audit trail",
            )}
          </p>
          <time>{new Date(e.at).toLocaleTimeString()}</time>
        </div>
      ))}
    </div>
  );
}
export function IntegrationActions({
  run,
  act,
  onRollback,
}: {
  run: Run;
  act: (fn: () => Promise<unknown>) => Promise<void>;
  onRollback: () => void;
}) {
  return (
    <div className="integration">
      {run.status === "partial" && (
        <button
          className="button primary"
          onClick={() => act(() => api.retry(run.id))}
        >
          Retry failed records
        </button>
      )}
      {["partial", "complete"].includes(run.status) && (
        <button className="button secondary" onClick={onRollback}>
          ↶ Roll back writes
        </button>
      )}
    </div>
  );
}
