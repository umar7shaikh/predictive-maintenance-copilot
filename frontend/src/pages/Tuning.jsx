import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Badge, Button, Card, CardHeader } from "../components/ui.jsx";

const METHODS = [
  { id: "zscore", label: "Z-Score", desc: "Global standard-deviation outliers" },
  { id: "rolling_z", label: "Rolling Z-Score", desc: "Deviation vs a trailing window" },
  { id: "ewma", label: "EWMA Residual", desc: "Exponentially-weighted moving average" },
  { id: "iqr", label: "IQR (Tukey)", desc: "Robust interquartile fences" },
  { id: "isolation_forest", label: "Isolation Forest", desc: "ML ensemble (scikit-learn)" },
];

export default function Tuning() {
  const [method, setMethod] = useState("zscore");
  const [threshold, setThreshold] = useState(3.0);
  const [window, setWindow] = useState(10);
  const [runs, setRuns] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  function loadRuns() {
    api.get("/detect/runs").then((r) => setRuns(r.data));
  }
  useEffect(loadRuns, []);

  async function rerun() {
    setBusy(true);
    setMsg("");
    try {
      const r = await api.post("/detect/rerun", { method, threshold, window });
      const m = r.data.metrics;
      setMsg(`Detected ${m.anomalies_detected} anomalies across ${m.machines_flagged} machines (${m.high_severity} high). Logged to MLflow.`);
      loadRuns();
    } catch (e) {
      setMsg(e?.response?.data?.detail || "Re-run failed.");
    } finally {
      setBusy(false);
    }
  }

  const windowDisabled = method === "zscore" || method === "iqr";

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <h1 className="mono text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          Detection&nbsp;Tuning
        </h1>
        <Link to="/" className="mono text-xs uppercase tracking-wider text-faint hover:text-fg">
          View fleet →
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader title="Parameters" subtitle="Re-runs on stored readings; logs an MLflow experiment" />
          <div className="space-y-5 p-5">
            <div>
              <label className="mono mb-2 block text-[10px] uppercase tracking-wider text-faint">Algorithm</label>
              <div className="space-y-1.5">
                {METHODS.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setMethod(m.id)}
                    className={`w-full rounded border px-3 py-2 text-left transition-colors ${
                      method === m.id ? "border-fg bg-panel2" : "border-hair hover:border-faint"
                    }`}
                  >
                    <div className="text-sm font-medium text-fg">{m.label}</div>
                    <div className="text-[11px] text-faint">{m.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <Slider
              label="Sensitivity threshold"
              value={threshold}
              min={1}
              max={6}
              step={0.5}
              onChange={setThreshold}
              hint="Lower = more sensitive"
            />
            <Slider
              label="Rolling window"
              value={window}
              min={2}
              max={30}
              step={1}
              onChange={setWindow}
              disabled={windowDisabled}
              hint={windowDisabled ? "Not used by this method" : "Points per window"}
            />

            <Button onClick={rerun} disabled={busy} className="w-full">
              {busy ? "Running…" : "Re-run detection"}
            </Button>
            {msg && <p className="mono text-[11px] leading-relaxed text-muted">{msg}</p>}
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader title="Experiment history" subtitle="Every re-run is tracked in MLflow — compare side by side" />
          <div className="max-h-[60vh] overflow-auto">
            <table className="w-full text-sm">
              <thead className="mono sticky top-0 bg-panel2 text-left text-[10px] uppercase tracking-wider text-faint">
                <tr>
                  <th className="px-4 py-2 font-medium">When</th>
                  <th className="px-4 py-2 font-medium">Method</th>
                  <th className="px-4 py-2 font-medium">Thr</th>
                  <th className="px-4 py-2 font-medium">Win</th>
                  <th className="px-4 py-2 font-medium">Anoms</th>
                  <th className="px-4 py-2 font-medium">Flagged</th>
                  <th className="px-4 py-2 font-medium">High</th>
                </tr>
              </thead>
              <tbody className="mono">
                {runs.map((run, i) => (
                  <tr key={run.id} className={`border-t border-hair ${i === 0 ? "bg-panel2/40" : ""}`}>
                    <td className="px-4 py-2 text-faint">{new Date(run.created_at).toLocaleTimeString()}</td>
                    <td className="px-4 py-2 text-fg">{run.params?.method || "—"}</td>
                    <td className="px-4 py-2 text-muted">{run.params?.threshold ?? "—"}</td>
                    <td className="px-4 py-2 text-muted">{run.params?.window ?? "—"}</td>
                    <td className="px-4 py-2 text-fg">{run.metrics?.anomalies_detected ?? "—"}</td>
                    <td className="px-4 py-2 text-muted">{run.metrics?.machines_flagged ?? "—"}</td>
                    <td className="px-4 py-2 text-crit">{run.metrics?.high_severity ?? "—"}</td>
                  </tr>
                ))}
                {runs.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-6 text-center text-faint">No runs yet — re-run detection to start an experiment.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Slider({ label, value, min, max, step, onChange, hint, disabled }) {
  return (
    <div className={disabled ? "opacity-40" : ""}>
      <div className="mb-1 flex items-center justify-between">
        <label className="mono text-[10px] uppercase tracking-wider text-faint">{label}</label>
        <span className="mono text-sm text-fg">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-fg"
      />
      {hint && <p className="mono mt-1 text-[10px] text-faint">{hint}</p>}
    </div>
  );
}
