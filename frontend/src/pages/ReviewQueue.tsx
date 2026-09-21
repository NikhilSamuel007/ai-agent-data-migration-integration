import type { Run } from "../types";
import { MappingCard, RecordCard } from "../components/EscalationCard";
import { reviewCount } from "../types";
export default function ReviewQueue({
  run,
  act,
}: {
  run: Run;
  act: (fn: () => Promise<unknown>) => Promise<void>;
}) {
  return (
    <>
      <div className="review-intro">
        <div>
          <h3>Decisions, with the context attached.</h3>
          <p>Resolve the uncertainty. The agent resumes automatically.</p>
        </div>
      </div>
      {run.files.flatMap((file) =>
        (file.mapping || [])
          .filter((m) => m.status === "pending")
          .map((mapping) => (
            <MappingCard
              key={`${file.name}:${mapping.header}`}
              {...{ run, file, mapping, act }}
            />
          )),
      )}
      {run.records
        .filter((r) => r.status === "review")
        .map((row) => (
          <RecordCard key={row.id} {...{ run, row, act }} />
        ))}
      {reviewCount(run) === 0 && (
        <div className="card empty">
          <div className="empty-icon">✓</div>
          <strong>You’re all caught up.</strong>
          <p>No uncertain cases are waiting for your review.</p>
        </div>
      )}
    </>
  );
}
