import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Badge, Button, Card, Kpi, Sparkline, StatusDot } from "../components/ui.jsx";

const SPARK_COLOR = { red: "#ef4444", yellow: "#f59e0b", green: "#7c8694" };
const LABEL = { red: "CRIT", yellow: "WARN", green: "OK" };
const UNIT = { temperature: "°C", pressure: "bar", vibration: "mm/s", rpm: "rpm" };

export default function Dashboard() {
  const [machines, setMachines] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/machines").then((r) => setMachines(r.data)).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="mono text-sm text-faint">LOADING FLEET…</p>;

  if (machines.length === 0) {
    return (
      <Card className="p-10 text-center">
        <h2 className="text-lg font-semibold text-fg">No machines online</h2>
        <p className="mt-1 text-sm text-muted">
          Upload a sensor CSV to detect anomalies and populate the fleet.
        </p>
        <Link to="/upload">
          <Button className="mt-4">Upload sensor data</Button>
        </Link>
      </Card>
    );
  }

  const critical = machines.filter((m) => m.health === "red").length;
  const anomalies = machines.reduce((a, m) => a + m.anomaly_count, 0);
  const trending = machines.reduce((a, m) => a + m.trending_count, 0);

  return (
    <div>
      <div className="mb-5 flex items-baseline justify-between">
        <h1 className="mono text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          Fleet&nbsp;Status
        </h1>
        <span className="mono text-[11px] text-faint">
          {new Date().toLocaleString()}
        </span>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi label="Machines" value={String(machines.length).padStart(2, "0")} />
        <Kpi
          label="Critical"
          value={String(critical).padStart(2, "0")}
          accent={critical ? "text-crit" : "text-fg"}
          sub={critical ? "● needs service" : "nominal"}
        />
        <Kpi label="Anomalies" value={anomalies} accent={anomalies ? "text-warn" : "text-fg"} />
        <Kpi label="Trending" value={trending} sub={trending ? "↗ worsening" : "stable"} />
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {machines.map((m) => (
          <Link key={m.id} to={`/machines/${m.id}`}>
            <Card className="p-4 transition-colors hover:border-faint">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <StatusDot health={m.health} pulse />
                  <div>
                    <p className="mono text-sm font-semibold text-fg">{m.name}</p>
                    <p className="text-[11px] uppercase tracking-wider text-faint">{m.machine_type}</p>
                  </div>
                </div>
                <Badge kind="health" value={m.health}>{LABEL[m.health]}</Badge>
              </div>

              <div className="mt-4 flex items-end justify-between">
                <div className="space-y-1">
                  <Readout label="TEMP" v={m.latest?.temperature} unit="°C" />
                  <Readout label="VIB" v={m.latest?.vibration} unit="mm/s" />
                </div>
                <div className="text-right">
                  <Sparkline data={m.spark} color={SPARK_COLOR[m.health]} width={110} height={34} />
                  <p className="mono mt-1 text-[10px] uppercase tracking-wider text-faint">
                    {m.spark_param}
                  </p>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-hair pt-3 text-[11px]">
                <div className="mono flex gap-3">
                  <Count n={m.high_count} label="HI" tone="text-crit" />
                  <Count n={m.medium_count} label="MD" tone="text-warn" />
                  <Count n={m.monitor_count} label="MN" tone="text-steel" />
                </div>
                <span className="mono text-faint">
                  {m.max_z ? `z=${m.max_z.toFixed(1)}` : "—"}
                </span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

function Readout({ label, v, unit }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="mono w-9 text-[10px] uppercase tracking-wider text-faint">{label}</span>
      <span className="mono text-sm text-fg">
        {v == null ? "—" : v.toFixed(1)}
        <span className="ml-0.5 text-[10px] text-faint">{unit}</span>
      </span>
    </div>
  );
}

function Count({ n, label, tone }) {
  return (
    <span className={n > 0 ? tone : "text-faint"}>
      {label} {n}
    </span>
  );
}
