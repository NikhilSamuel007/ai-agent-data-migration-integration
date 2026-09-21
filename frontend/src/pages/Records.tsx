import type { Run } from "../types";
import { Status, IntegrationActions } from "../components/Shared";
export default function Records(props: {
  run: Run;
  act: (fn: () => Promise<unknown>) => Promise<void>;
  onRollback: () => void;
}) {
  return (
    <>
      <section className="card">
        <div className="card-head">
          <h3>Reconciled employee records</h3>
          <small>{props.run.records.length} source rows retained</small>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Employee</th>
                <th>Department</th>
                <th>Date of birth</th>
                <th>Employment / account</th>
                <th>Source</th>
                <th>Delivery</th>
              </tr>
            </thead>
            <tbody>
              {props.run.records.map((r) => (
                <tr key={r.id}>
                  <td>
                    <strong>{[r.data.first_name, r.data.last_name].filter(Boolean).join(" ")}</strong>
                    <small>{r.data.email}</small>
                  </td>
                  <td>{r.data.department}</td>
                  <td>{r.data.date_of_birth}</td>
                  <td>{r.data.employment_status}<small>{r.data.account_status || "Not supplied"}</small></td>
                  <td>
                    {r.file}
                    <small>Row {r.row}</small>
                  </td>
                  <td>
                    <Status value={r.status} />
                    <small>{r.attempts} attempts</small>
                    {r.targetId && (
                      <small title={r.targetId}>
                        Target {r.targetId.slice(0, 12)}…
                      </small>
                    )}
                    {r.integrationError && (
                      <small className="record-error">
                        {r.integrationError}
                      </small>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <IntegrationActions {...props} />
    </>
  );
}
