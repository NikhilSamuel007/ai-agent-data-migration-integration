import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Run, RunSummary, View } from "./types";
import { statuses, reviewCount } from "./types";
import { MigrationStats, Status } from "./components/Shared";
import Dashboard from "./pages/Dashboard";
import ReviewQueue from "./pages/ReviewQueue";
import Records from "./pages/Records";
import Audit from "./pages/Audit";

export default function App() {
  const [run, setRun] = useState<Run | null>(null),
    [history, setHistory] = useState<RunSummary[]>([]),
    [view, setView] = useState<View>("overview"),
    [setup, setSetup] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [selected, setSelected] = useState<string | null>(null),
    [schema, setSchema] = useState<
      Record<string, { type: string; required: boolean; enum?: string[]; description?: string }>
    >({});
  const dialog = useRef<HTMLDialogElement>(null),
    actionLock = useRef(false),
    setupTouched = useRef(false),
    selectedRef = useRef<string | null>(null);
  const loadHistory = async () => {
    const list = await api.runs();
    setHistory(list);
    return list;
  };
  const selectRun = async (id: string, initial = false) => {
    selectedRef.current = id;
    setSelected(id);
    const result = await api.run(id);
    if (selectedRef.current === id) {
      setRun(result);
      if (!initial || !setupTouched.current) setSetup(false);
      localStorage.setItem("relay-run", id);
    }
  };
  useEffect(() => {
    let active = true;
    api
      .runs()
      .then((list) => {
        if (!active || selectedRef.current) return;
        setHistory(list);
        const saved = localStorage.getItem("relay-run");
        if (list.length)
          void selectRun(
            list.some((r) => r.id === saved) ? saved! : list[0].id,
            true,
          ).catch((e) => setError(e.message));
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    api
      .schema()
      .then((s) => {
        if (active) setSchema(s.fields);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!selected) return;
    let stopped = false;
    const poll = async () => {
      if (actionLock.current) return;
      try {
        const next = await api.run(selected);
        if (!stopped && selectedRef.current === selected) setRun(next);
      } catch (e) {
        if (!stopped) setError((e as Error).message);
      }
    };
    const timer = setInterval(poll, 1200);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [selected]);
  const act = async (fn: () => Promise<unknown>) => {
    if (actionLock.current) return;
    actionLock.current = true;
    setBusy(true);
    setError("");
    try {
      await fn();
      if (selectedRef.current) setRun(await api.run(selectedRef.current));
      await loadHistory();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      actionLock.current = false;
      setBusy(false);
    }
  };
  const rollback = () => dialog.current?.showModal();
  const begin = async (demo: boolean, form?: HTMLFormElement) => {
    await act(async () => {
      const result = demo
        ? await api.demo()
        : await api.upload(new FormData(form));
      setView("overview");
      await selectRun(result.id);
    });
  };
  return (
    <>
      <aside className="sidebar">
        <a className="brand" href="/">
          <span className="brand-mark">r</span>relay
          <span className="brand-dot">.</span>
        </a>
        <div className="workspace-label">IMPLEMENTATION WORKSPACE</div>
        <div className="workspace">
          <span className="avatar">N</span>
          <div>
            Northstar<small>Client operations</small>
          </div>
        </div>
        <nav aria-label="Main navigation">
          {(
            [
              ["overview", "▦", "Migration workspace"],
              ["review", "⊙", "Review queue"],
              ["audit", "≡", "Activity & audit"],
              ["schema", "◇", "Target schema"],
            ] as const
          ).map(([key, icon, label]) => (
            <button
              className={`nav ${view === key ? "active" : ""}`}
              key={key}
              onClick={() => setView(key)}
            >
              <span>{icon}</span>
              {label}
              {key === "review" && <b>{run ? reviewCount(run) : 0}</b>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="local-dot" />
          Local workspace<small>Human judgment. Traceable decisions.</small>
          <div className="profile">
            <span className="avatar">IC</span>
            <div>
              Implementation consultant<small>Local operator</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="app">
        <header>
          <div>
            <span className="muted">Workspace</span>
            <span className="slash">/</span>Employee migration
          </div>
          <span className="header-label">MOCK TARGET ENVIRONMENT</span>
        </header>
        <main aria-busy={busy}>
          <div className="heading">
            <div className="eyebrow">DATA MIGRATION</div>
            <div className="title-row">
              <div>
                <h1>Move the data. Keep the context.</h1>
                <p className="subtitle">
                  Your agent handles the routine. You make the judgment calls.
                </p>
              </div>
              <button
                id="new-btn"
                className="button primary"
                onClick={() => {
                  setupTouched.current = true;
                  setSetup(true);
                }}
              >
                ＋ New migration
              </button>
            </div>
          </div>
          {error && (
            <div id="toast" role="alert">
              {error}
            </div>
          )}
          <fieldset disabled={busy} className="work-area">
            {setup && (
              <section className="setup" id="setup">
                <div>
                  <span className="section-kicker">START A MIGRATION</span>
                  <h2>Bring your source files together.</h2>
                  <p>
                    Upload CSV and Excel exports. The agent profiles, maps,
                    cleans, and reconciles them into one employee dataset.
                  </p>
                  <div className="setup-actions">
                    <button
                      type="button"
                      className="button primary"
                      id="demo-btn"
                      onClick={() => begin(true)}
                    >
                      Try sample migration →
                    </button>
                    <span>
                      3 files · 8 source rows · status review · retry recovery
                    </span>
                  </div>
                </div>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void begin(false, e.currentTarget);
                  }}
                >
                  <label><input type="checkbox" name="simulate_failure" value="true" /> Simulate target failures (demo only)</label>
                  <label htmlFor="migration-name">Migration name</label>
                  <input
                    id="migration-name"
                    name="name"
                    placeholder="e.g. Northstar employee import"
                  />
                  <label htmlFor="files" className="file-zone">
                    <span className="upload-icon">↥</span>
                    <strong>Choose source files</strong>
                    <small>CSV or XLSX · up to 5 files, 5 MB each</small>
                    <input
                      id="files"
                      name="files"
                      type="file"
                      multiple
                      accept=".csv,.xlsx"
                      required
                    />
                  </label>
                  <button className="button secondary">Start migration</button>
                </form>
              </section>
            )}
            {view === "schema" ? (
              <section className="card">
                <div className="card-head">
                  <h3>Target employee schema</h3>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Field</th>
                        <th>Type</th>
                        <th>Required</th>
                        <th>Allowed values / meaning</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(schema).map(([key, value]) => (
                        <tr key={key}>
                          <td>{key}</td>
                          <td>{value.type}</td>
                          <td>{value.required ? "Yes" : "No"}</td>
                          <td>{value.enum?.join(", ") || "—"}<small>{value.description}</small></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ) : (
              run && (
                <div id="run-area">
                  <div className="run-bar">
                    <div>
                      <span className="run-icon">↗</span>
                      <strong>{run.name}</strong>
                      <Status id="run-status" value={run.status} />
                    </div>
                    <select
                      id="history"
                      aria-label="Migration history"
                      value={run.id}
                      onChange={(e) => act(() => selectRun(e.target.value))}
                    >
                      {history.map((h) => (
                        <option value={h.id} key={h.id}>
                          {h.name} ·{" "}
                          {statuses[h.id === run.id ? run.status : h.status]}
                        </option>
                      ))}
                    </select>
                  </div>
                  <MigrationStats run={run} />
                  <div
                    className="tabs"
                    role="tablist"
                    aria-label="Migration details"
                  >
                    {(
                      [
                        ["overview", "Overview"],
                        ["review", "Review queue"],
                        ["records", "All records"],
                        ["audit", "Audit trail"],
                      ] as const
                    ).map(([key, label]) => (
                      <button
                        key={key}
                        role="tab"
                        aria-selected={view === key}
                        className={view === key ? "active" : ""}
                        onClick={() => setView(key)}
                      >
                        {label}
                        {key === "review" && <span>{reviewCount(run)}</span>}
                      </button>
                    ))}
                  </div>
                  <div id="view-content">
                    {view === "overview" ? (
                      <Dashboard
                        {...{ run, setView, act, onRollback: rollback }}
                      />
                    ) : view === "review" ? (
                      <ReviewQueue {...{ run, act }} />
                    ) : view === "records" ? (
                      <Records {...{ run, act, onRollback: rollback }} />
                    ) : (
                      <Audit run={run} />
                    )}
                  </div>
                </div>
              )
            )}
          </fieldset>
          <footer>
            <span>RELAY / CONTROLLED AUTONOMY</span>
            <span>Traceable decisions. Reversible writes.</span>
          </footer>
        </main>
      </div>
      <dialog ref={dialog}>
        <form method="dialog">
          <div className="section-kicker">ROLL BACK MIGRATION</div>
          <h2>Remove this migration’s writes?</h2>
          <p>
            Only target inserts owned by this run will be removed. Source data
            and audit history remain.
          </p>
          <div className="dialog-actions">
            <button className="button secondary">Keep records</button>
            <button
              className="button danger"
              onClick={() => {
                if (run) void act(() => api.rollback(run.id));
              }}
            >
              Roll back writes
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}
