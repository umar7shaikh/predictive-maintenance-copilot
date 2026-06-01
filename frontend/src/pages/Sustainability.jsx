import { useEffect, useState } from "react";
import api from "../lib/api";
import { Button, Card, CardHeader, Input, Kpi } from "../components/ui.jsx";

const fmt = (n) => (n == null ? "—" : Number(n).toLocaleString());
const today = () => new Date().toISOString().slice(0, 10);
const monthAgo = () => {
  const d = new Date();
  d.setMonth(d.getMonth() - 1);
  return d.toISOString().slice(0, 10);
};

export default function Sustainability() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = () =>
    api.get("/carbon/summary").then((r) => setData(r.data)).finally(() => setLoading(false));

  useEffect(() => {
    load();
  }, []);

  if (loading) return <p className="mono text-sm text-faint">LOADING CARBON INVENTORY…</p>;

  const cur = data.currency || "INR";
  const waste = data.waste || {};

  return (
    <div>
      <div className="mb-5 flex items-baseline justify-between">
        <h1 className="mono text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          Carbon&nbsp;&amp;&nbsp;Energy
        </h1>
        <div className="flex items-center gap-3">
          <a href="/api/export/sustainability.csv" className="mono text-[11px] text-faint hover:text-fg">
            ↓ EXPORT CSV
          </a>
          <Button
            variant="ghost"
            className="text-xs"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              await api.post("/carbon/recompute").then((r) => setData(r.data));
              setBusy(false);
            }}
          >
            {busy ? "Recomputing…" : "Recompute"}
          </Button>
        </div>
      </div>

      {/* --- headline KPIs --- */}
      <div className="mb-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Kpi label="Total CO₂e" value={fmt(data.total_tonnes_co2e)} sub="tonnes" accent="text-fg" />
        <Kpi label="Scope 1" value={fmt(data.scope1_kgco2e)} sub="kgCO₂e · direct/fuel" />
        <Kpi label="Scope 2" value={fmt(data.scope2_kgco2e)} sub="kgCO₂e · electricity" />
        <Kpi label="Energy" value={fmt(data.total_kwh)} sub="kWh purchased" />
        <Kpi label="Energy cost" value={fmt(data.total_energy_cost)} sub={cur} />
        <Kpi
          label="Avoidable"
          value={fmt(waste.wasted_kgco2e)}
          sub={`kgCO₂e · ~${fmt(waste.saveable_cost)} ${waste.currency || cur}`}
          accent={waste.wasted_kgco2e ? "text-warn" : "text-fg"}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {/* --- energy waste from degradation (the PdM link) --- */}
        <Card className="lg:col-span-2">
          <CardHeader
            title="Energy waste from degradation"
            subtitle="Estimated extra energy a deteriorating machine burns — decision-support, not booked emissions"
          />
          <div className="p-4">
            {(!waste.machines || waste.machines.length === 0) ? (
              <p className="text-sm text-muted">
                No estimate yet. Set a machine's <span className="mono">rated power (kW)</span> below
                and detect anomalies — wasted energy is then estimated from severity.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="mono text-[10px] uppercase tracking-wider text-faint">
                    <th className="pb-2 text-left">Machine</th>
                    <th className="pb-2 text-right">Severity</th>
                    <th className="pb-2 text-right">Wasted kWh</th>
                    <th className="pb-2 text-right">kgCO₂e</th>
                    <th className="pb-2 text-right">Saveable</th>
                  </tr>
                </thead>
                <tbody className="mono">
                  {waste.machines.map((w) => (
                    <tr key={w.machine_id} className="border-t border-hair">
                      <td className="py-1.5 text-fg">{w.machine}</td>
                      <td className="py-1.5 text-right text-faint">{w.severity}</td>
                      <td className="py-1.5 text-right text-fg">{fmt(w.wasted_kwh)}</td>
                      <td className="py-1.5 text-right text-warn">{fmt(w.wasted_kgco2e)}</td>
                      <td className="py-1.5 text-right text-fg">
                        {fmt(w.saveable_cost)} <span className="text-faint">{w.currency}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>

        {/* --- emissions by source --- */}
        <Card>
          <CardHeader title="By source" subtitle="kgCO₂e" />
          <div className="p-4">
            {(!data.by_source || data.by_source.length === 0) ? (
              <p className="text-sm text-muted">No emissions recorded yet.</p>
            ) : (
              <ScopeBars items={data.by_source} />
            )}
          </div>
        </Card>
      </div>

      {/* --- data input --- */}
      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <BillForm cur={cur} onSaved={load} />
        <FuelForm cur={cur} onSaved={load} />
      </div>

      <RatedPower onSaved={load} />

      {/* --- factor provenance --- */}
      <Card className="mt-3">
        <CardHeader title="Emission factors in use" subtitle="Provenance travels with every number — replace defaults with your region/year official factors before filing" />
        <div className="p-4 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="mono text-[10px] uppercase tracking-wider text-faint">
                <th className="pb-2 text-left">Region</th>
                <th className="pb-2 text-left">Activity</th>
                <th className="pb-2 text-right">Scope</th>
                <th className="pb-2 text-right">Factor</th>
                <th className="pb-2 text-left pl-4">Source</th>
              </tr>
            </thead>
            <tbody className="mono">
              {(data.factors || []).map((f, i) => (
                <tr key={i} className="border-t border-hair">
                  <td className="py-1 text-fg">{f.region}</td>
                  <td className="py-1 text-muted">{f.activity_type}</td>
                  <td className="py-1 text-right text-faint">{f.scope}</td>
                  <td className="py-1 text-right text-fg">
                    {f.kgco2e_per_unit} <span className="text-faint">/{f.unit}</span>
                  </td>
                  <td className="py-1 pl-4 text-faint">{f.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function ScopeBars({ items }) {
  const max = Math.max(...items.map((i) => i.kgco2e), 1);
  return (
    <div className="space-y-2.5">
      {items.map((it) => (
        <div key={it.source}>
          <div className="mono flex justify-between text-[11px]">
            <span className="text-muted">{it.source}</span>
            <span className="text-fg">{fmt(it.kgco2e)}</span>
          </div>
          <div className="mt-1 h-1.5 rounded bg-panel2">
            <div className="h-1.5 rounded bg-steel" style={{ width: `${(it.kgco2e / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function BillForm({ cur, onSaved }) {
  const [f, setF] = useState({ kwh: "", cost: "", region: "IN", period_start: monthAgo(), period_end: today() });
  const [msg, setMsg] = useState("");
  const submit = async () => {
    setMsg("");
    try {
      await api.post("/carbon/bills", {
        kwh: Number(f.kwh),
        cost: f.cost ? Number(f.cost) : null,
        region: f.region,
        currency: cur,
        period_start: new Date(f.period_start).toISOString(),
        period_end: new Date(f.period_end).toISOString(),
      });
      setF({ ...f, kwh: "", cost: "" });
      setMsg("Saved ✓");
      onSaved();
    } catch (e) {
      setMsg(e.response?.data?.detail || "Failed");
    }
  };
  return (
    <Card>
      <CardHeader title="Add electricity bill" subtitle="Scope 2 — no sensors needed" />
      <div className="space-y-2 p-4">
        <div className="grid grid-cols-2 gap-2">
          <Field label="kWh"><Input type="number" value={f.kwh} onChange={(e) => setF({ ...f, kwh: e.target.value })} /></Field>
          <Field label={`Bill amount (${cur})`}><Input type="number" value={f.cost} onChange={(e) => setF({ ...f, cost: e.target.value })} /></Field>
          <Field label="Period start"><Input type="date" value={f.period_start} onChange={(e) => setF({ ...f, period_start: e.target.value })} /></Field>
          <Field label="Period end"><Input type="date" value={f.period_end} onChange={(e) => setF({ ...f, period_end: e.target.value })} /></Field>
          <Field label="Region"><RegionSelect value={f.region} onChange={(v) => setF({ ...f, region: v })} /></Field>
        </div>
        <div className="flex items-center gap-3 pt-1">
          <Button onClick={submit} disabled={!f.kwh}>Add bill</Button>
          {msg && <span className="mono text-[11px] text-faint">{msg}</span>}
        </div>
      </div>
    </Card>
  );
}

function FuelForm({ cur, onSaved }) {
  const [f, setF] = useState({ litres: "", runtime_hours: "", cost: "", region: "IN", period_start: monthAgo(), period_end: today() });
  const [msg, setMsg] = useState("");
  const submit = async () => {
    setMsg("");
    try {
      await api.post("/carbon/fuel", {
        fuel_type: "diesel",
        litres: f.litres ? Number(f.litres) : null,
        runtime_hours: f.runtime_hours ? Number(f.runtime_hours) : null,
        cost: f.cost ? Number(f.cost) : null,
        region: f.region,
        currency: cur,
        period_start: new Date(f.period_start).toISOString(),
        period_end: new Date(f.period_end).toISOString(),
      });
      setF({ ...f, litres: "", runtime_hours: "", cost: "" });
      setMsg("Saved ✓");
      onSaved();
    } catch (e) {
      setMsg(e.response?.data?.detail || "Failed");
    }
  };
  return (
    <Card>
      <CardHeader title="Add diesel / genset" subtitle="Scope 1 — litres, or runtime hours (estimated)" />
      <div className="space-y-2 p-4">
        <div className="grid grid-cols-2 gap-2">
          <Field label="Litres"><Input type="number" value={f.litres} onChange={(e) => setF({ ...f, litres: e.target.value })} /></Field>
          <Field label="…or runtime hrs"><Input type="number" value={f.runtime_hours} onChange={(e) => setF({ ...f, runtime_hours: e.target.value })} /></Field>
          <Field label={`Cost (${cur})`}><Input type="number" value={f.cost} onChange={(e) => setF({ ...f, cost: e.target.value })} /></Field>
          <Field label="Region"><RegionSelect value={f.region} onChange={(v) => setF({ ...f, region: v })} /></Field>
          <Field label="Period start"><Input type="date" value={f.period_start} onChange={(e) => setF({ ...f, period_start: e.target.value })} /></Field>
          <Field label="Period end"><Input type="date" value={f.period_end} onChange={(e) => setF({ ...f, period_end: e.target.value })} /></Field>
        </div>
        <div className="flex items-center gap-3 pt-1">
          <Button onClick={submit} disabled={!f.litres && !f.runtime_hours}>Add fuel</Button>
          {msg && <span className="mono text-[11px] text-faint">{msg}</span>}
        </div>
      </div>
    </Card>
  );
}

function RatedPower({ onSaved }) {
  const [machines, setMachines] = useState([]);
  const [sel, setSel] = useState("");
  const [kw, setKw] = useState("");
  const [msg, setMsg] = useState("");
  useEffect(() => {
    api.get("/machines").then((r) => setMachines(r.data));
  }, []);
  const submit = async () => {
    setMsg("");
    try {
      await api.patch(`/carbon/machines/${sel}/rated-power`, { rated_power_kw: Number(kw) });
      setMsg("Saved ✓");
      onSaved();
    } catch (e) {
      setMsg(e.response?.data?.detail || "Failed");
    }
  };
  return (
    <Card className="mt-3">
      <CardHeader title="Machine rated power" subtitle="Set nameplate kW so energy waste can be estimated" />
      <div className="flex flex-wrap items-end gap-3 p-4">
        <Field label="Machine">
          <select
            className="w-48 rounded border border-hair bg-panel2 px-3 py-2 text-sm text-fg outline-none focus:border-faint"
            value={sel}
            onChange={(e) => setSel(e.target.value)}
          >
            <option value="">Select…</option>
            {machines.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </Field>
        <Field label="Rated power (kW)">
          <Input type="number" className="w-32" value={kw} onChange={(e) => setKw(e.target.value)} />
        </Field>
        <Button onClick={submit} disabled={!sel || !kw}>Save</Button>
        {msg && <span className="mono text-[11px] text-faint">{msg}</span>}
      </div>
    </Card>
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

const REGIONS = ["IN", "ZA", "MY", "TH", "ID", "VN", "NG", "KE", "GLOBAL"];
function RegionSelect({ value, onChange }) {
  return (
    <select
      className="w-full rounded border border-hair bg-panel2 px-3 py-2 text-sm text-fg outline-none focus:border-faint"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {REGIONS.map((r) => (
        <option key={r} value={r}>{r}</option>
      ))}
    </select>
  );
}
