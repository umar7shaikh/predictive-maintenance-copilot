import { useEffect, useState } from "react";
import api from "../lib/api";
import { Badge, Button, Card, CardHeader, Input } from "../components/ui.jsx";

const today = () => new Date().toISOString().slice(0, 10);
const yearStart = () => `${new Date().getFullYear()}-01-01`;

export default function Reports() {
  const [frameworks, setFrameworks] = useState([]);
  const [reports, setReports] = useState([]);
  const [f, setF] = useState({
    framework: "ISSB", region: "IN",
    period_start: yearStart(), period_end: today(), production_tonnes: "",
  });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const [audit, setAudit] = useState([]);
  const [integrity, setIntegrity] = useState(null);

  const load = () => {
    api.get("/reports").then((r) => setReports(r.data));
    api.get("/audit").then((r) => setAudit(r.data)).catch(() => {});
    api.get("/audit/verify").then((r) => setIntegrity(r.data)).catch(() => {});
  };
  useEffect(() => {
    api.get("/reports/frameworks").then((r) => setFrameworks(r.data));
    load();
  }, []);

  const generate = async () => {
    setBusy(true);
    setMsg("");
    try {
      await api.post("/reports/generate", {
        framework: f.framework,
        region: f.region,
        period_start: new Date(f.period_start).toISOString(),
        period_end: new Date(f.period_end).toISOString(),
        production_tonnes: f.production_tonnes ? Number(f.production_tonnes) : null,
      });
      setMsg("Generated ✓");
      load();
    } catch (e) {
      setMsg(e.response?.data?.detail || "Failed");
    }
    setBusy(false);
  };

  const token = localStorage.getItem("pdm_token");
  const openHtml = async (id) => {
    // Authenticated fetch -> blob -> new tab (endpoint requires the bearer token).
    const res = await fetch(`/api/reports/${id}/html`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await res.blob();
    window.open(URL.createObjectURL(blob), "_blank");
  };

  return (
    <div>
      <div className="mb-5 flex items-baseline justify-between">
        <h1 className="mono text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          Regulatory&nbsp;Reports
        </h1>
        <span className="mono text-[11px] text-faint">{reports.length} generated</span>
      </div>

      <Card className="mb-3">
        <CardHeader
          title="Generate report"
          subtitle="Built from the audited carbon inventory — methodology + factor provenance included"
        />
        <div className="p-4">
          <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
            <Field label="Framework">
              <select
                className="w-full rounded border border-hair bg-panel2 px-3 py-2 text-sm text-fg outline-none focus:border-faint"
                value={f.framework}
                onChange={(e) => setF({ ...f, framework: e.target.value })}
              >
                {frameworks.map((fr) => (
                  <option key={fr.id} value={fr.id}>{fr.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Region">
              <select
                className="w-full rounded border border-hair bg-panel2 px-3 py-2 text-sm text-fg outline-none focus:border-faint"
                value={f.region}
                onChange={(e) => setF({ ...f, region: e.target.value })}
              >
                {["IN", "ZA", "MY", "TH", "ID", "VN", "NG", "KE", "GLOBAL"].map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </Field>
            <Field label="Period start">
              <Input type="date" value={f.period_start} onChange={(e) => setF({ ...f, period_start: e.target.value })} />
            </Field>
            <Field label="Period end">
              <Input type="date" value={f.period_end} onChange={(e) => setF({ ...f, period_end: e.target.value })} />
            </Field>
            {f.framework === "CBAM" && (
              <Field label="Production (tonnes)">
                <Input type="number" value={f.production_tonnes} onChange={(e) => setF({ ...f, production_tonnes: e.target.value })} />
              </Field>
            )}
          </div>
          <div className="flex items-center gap-3">
            <Button onClick={generate} disabled={busy}>{busy ? "Generating…" : "Generate"}</Button>
            {msg && <span className="mono text-[11px] text-faint">{msg}</span>}
          </div>
          {f.framework === "CBAM" && (
            <p className="mt-3 text-[11px] text-faint">
              CBAM intensity = total embedded emissions ÷ production tonnes. Leave blank to report totals only.
            </p>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title="Generated reports" />
        <div className="divide-y divide-hair">
          {reports.length === 0 ? (
            <p className="p-5 text-sm text-muted">No reports yet. Generate one above.</p>
          ) : (
            reports.map((r) => (
              <div key={r.id} className="flex items-center justify-between px-5 py-3">
                <div className="flex items-center gap-3">
                  <Badge kind="verdict" value="MONITOR">{r.framework}</Badge>
                  <div>
                    <p className="text-sm text-fg">{r.title}</p>
                    <p className="mono text-[11px] text-faint">
                      {r.region} · {r.period_start.slice(0, 10)} → {r.period_end.slice(0, 10)} · {r.status}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" className="text-xs" onClick={() => openHtml(r.id)}>
                    View / print
                  </Button>
                  <Button
                    variant="ghost"
                    className="text-xs"
                    onClick={async () => {
                      await api.delete(`/reports/${r.id}`);
                      load();
                    }}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>

      {/* --- assurance / tamper-evident audit trail --- */}
      <Card className="mt-3">
        <CardHeader
          title="Assurance — audit trail"
          subtitle="Append-only, hash-chained log of report generation. Tamper-evident for external assurance."
          right={
            integrity && (
              <span className={`mono text-[11px] ${integrity.valid ? "text-steel" : "text-crit"}`}>
                {integrity.valid ? `✓ INTACT · ${integrity.events} events` : `✗ BROKEN at #${integrity.broken_at}`}
              </span>
            )
          }
        />
        <div className="p-4">
          {audit.length === 0 ? (
            <p className="text-sm text-muted">No audited actions yet. Generate a report to start the chain.</p>
          ) : (
            <ul className="space-y-1.5">
              {audit.map((ev) => (
                <li key={ev.id} className="flex items-center justify-between border-b border-hair pb-1.5 text-[12px]">
                  <div className="flex items-center gap-2">
                    <span className="mono text-faint">#{ev.seq}</span>
                    <span className="text-fg">{ev.summary}</span>
                  </div>
                  <span className="mono text-[10px] text-faint" title={ev.hash}>
                    {ev.actor} · {ev.hash.slice(0, 10)}…
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Card>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mono mb-1 block text-[10px] uppercase tracking-wider text-faint">{label}</span>
      {children}
    </label>
  );
}
