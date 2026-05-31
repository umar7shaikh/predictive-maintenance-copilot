import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../lib/api";
import { Badge, Button, Card, CardHeader, StatusDot } from "../components/ui.jsx";

const PARAMS = [
  { key: "temperature", label: "Temperature", unit: "°C", color: "#ef4444" },
  { key: "pressure", label: "Pressure", unit: "bar", color: "#7c8694" },
  { key: "vibration", label: "Vibration", unit: "mm/s", color: "#f59e0b" },
  { key: "rpm", label: "RPM", unit: "rpm", color: "#9a958c" },
];

export default function MachineDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    api.get(`/machines/${id}`).then((r) => setDetail(r.data));
  }, [id]);

  async function deleteMachine() {
    if (!confirm(`Delete ${detail.machine.name} and all its readings/anomalies?`)) return;
    await api.delete(`/machines/${id}`);
    navigate("/");
  }

  const anomalyByParam = useMemo(() => {
    const map = {};
    (detail?.anomalies || []).forEach((a) => {
      (map[a.parameter] ||= new Set()).add(new Date(a.ts).getTime());
    });
    return map;
  }, [detail]);

  if (!detail) return <p className="mono text-sm text-faint">LOADING…</p>;
  const { machine, readings, anomalies } = detail;
  const chartData = readings.map((r) => ({ ...r, t: new Date(r.ts).getTime() }));

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/" className="mono text-xs uppercase tracking-wider text-faint hover:text-fg">
            ← Fleet
          </Link>
          <StatusDot health={machine.health} pulse />
          <h1 className="mono text-lg font-semibold text-fg">{machine.name}</h1>
          <Badge kind="health" value={machine.health} />
          <span className="text-xs uppercase tracking-wider text-faint">{machine.machine_type}</span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" onClick={deleteMachine}>Delete</Button>
          <Link to={`/assistant?machine=${machine.id}`}>
            <Button>Ask the AI Copilot</Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {PARAMS.map((p) => (
          <Card key={p.key}>
            <CardHeader
              title={`${p.label} · ${p.unit}`}
              subtitle={`${anomalyByParam[p.key]?.size || 0} anomalies`}
            />
            <div className="h-56 p-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 12, bottom: 0, left: -14 }}>
                  <CartesianGrid stroke="#222226" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="t"
                    type="number"
                    domain={["dataMin", "dataMax"]}
                    tickFormatter={(t) => new Date(t).toLocaleDateString()}
                    tick={{ fill: "#6b675f", fontSize: 10 }}
                    stroke="#2a2a2f"
                  />
                  <YAxis tick={{ fill: "#6b675f", fontSize: 10 }} domain={["auto", "auto"]} stroke="#2a2a2f" />
                  <Tooltip
                    contentStyle={{
                      background: "#161619",
                      border: "1px solid #2a2a2f",
                      borderRadius: 6,
                      fontSize: 12,
                      color: "#e8e6e1",
                    }}
                    labelStyle={{ color: "#9a958c" }}
                    labelFormatter={(t) => new Date(t).toLocaleString()}
                  />
                  <Legend wrapperStyle={{ fontSize: 11, color: "#9a958c" }} />
                  <Line
                    name={p.label}
                    type="monotone"
                    dataKey={p.key}
                    stroke={p.color}
                    strokeWidth={1.5}
                    dot={(props) => <AnomalyDot {...props} anomalies={anomalyByParam[p.key]} />}
                    isAnimationActive={false}
                  />
                  <Line
                    name="Rolling avg"
                    type="monotone"
                    dataKey={`${p.key}_roll_avg`}
                    stroke="#52525b"
                    strokeWidth={1}
                    strokeDasharray="4 3"
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        ))}
      </div>

      <Card className="mt-4">
        <CardHeader title="Detected anomalies" subtitle={`${anomalies.length} total`} />
        <div className="max-h-80 overflow-auto">
          <table className="w-full text-sm">
            <thead className="mono sticky top-0 bg-panel2 text-left text-[10px] uppercase tracking-wider text-faint">
              <tr>
                <th className="px-4 py-2 font-medium">Parameter</th>
                <th className="px-4 py-2 font-medium">Time</th>
                <th className="px-4 py-2 font-medium">Value</th>
                <th className="px-4 py-2 font-medium">z-score</th>
                <th className="px-4 py-2 font-medium">Severity</th>
                <th className="px-4 py-2 font-medium">Trend</th>
              </tr>
            </thead>
            <tbody className="mono">
              {anomalies.map((a) => (
                <tr key={a.id} className="border-t border-hair">
                  <td className="px-4 py-2 capitalize text-fg">{a.parameter}</td>
                  <td className="px-4 py-2 text-faint">{new Date(a.ts).toLocaleString()}</td>
                  <td className="px-4 py-2 text-fg">{a.value.toFixed(2)}</td>
                  <td className="px-4 py-2 text-fg">{a.z_score.toFixed(2)}</td>
                  <td className="px-4 py-2"><Badge kind="severity" value={a.severity} /></td>
                  <td className="px-4 py-2 text-warn">{a.is_trending ? "↗ worsening" : "—"}</td>
                </tr>
              ))}
              {anomalies.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-6 text-center text-faint">No anomalies detected.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function AnomalyDot({ cx, cy, payload, anomalies }) {
  if (cx == null || cy == null || !anomalies?.has(payload.t)) return null;
  return <circle cx={cx} cy={cy} r={3.5} fill="#ef4444" stroke="#0d0d0f" strokeWidth={1.5} />;
}
