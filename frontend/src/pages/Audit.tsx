import type { Run } from "../types";
import { apiUrl } from "../api";
export default function Audit({ run }: { run: Run }) {
  return (
    <section className="card">
      <div className="card-head">
        <h3>Every action, accounted for.</h3>
        <a
          className="button secondary"
          href={apiUrl(`/api/runs/${run.id}/audit`)}
          download
        >
          ↓ Export audit
        </a>
      </div>
      {run.events.map((e) => (
        <details className="audit-row" key={e.seq}>
          <summary>
            <strong>{e.action}</strong>
            <small>
              #{e.seq} · {new Date(e.at).toLocaleString()}
            </small>
          </summary>
          <pre>{JSON.stringify(e.detail, null, 2)}</pre>
        </details>
      ))}
    </section>
  );
}
