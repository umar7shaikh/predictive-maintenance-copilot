import { useEffect, useState } from "react";
import api from "../lib/api";
import { Badge, Button, Card, CardHeader } from "../components/ui.jsx";

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [recs, setRecs] = useState({});

  function refresh() {
    api.get("/logs").then((r) => setLogs(r.data));
    api.get("/recommendations").then((r) => {
      const map = {};
      r.data.forEach((rec) => (map[rec.id] = rec));
      setRecs(map);
    });
  }

  useEffect(refresh, []);

  async function toggle(log) {
    await api.patch(`/logs/${log.id}`, { actioned: !log.actioned });
    refresh();
  }

  async function saveNote(log, notes) {
    await api.patch(`/logs/${log.id}`, { notes });
    refresh();
  }

  async function remove(log) {
    if (!confirm("Delete this log entry?")) return;
    await api.delete(`/logs/${log.id}`);
    refresh();
  }

  return (
    <div>
      <h1 className="mono mb-5 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
        Maintenance&nbsp;Log
      </h1>
      <Card>
        <CardHeader title="Audit trail" subtitle="Saved AI recommendations and actions taken" />
        <ul className="divide-y divide-hair">
          {logs.map((log) => {
            const rec = recs[log.recommendation_id];
            return (
              <li key={log.id} className="px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      {rec && <Badge kind="verdict" value={rec.verdict} />}
                      <span className="mono text-[11px] text-faint">
                        {new Date(log.created_at).toLocaleString()}
                      </span>
                    </div>
                    {rec && (
                      <>
                        <p className="mt-1.5 text-sm font-medium text-fg">{rec.question}</p>
                        <p className="mt-0.5 text-sm leading-relaxed text-muted">{rec.explanation}</p>
                      </>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Button
                      variant={log.actioned ? "ghost" : "primary"}
                      onClick={() => toggle(log)}
                    >
                      {log.actioned ? "Actioned ✓" : "Mark actioned"}
                    </Button>
                    <button
                      onClick={() => remove(log)}
                      title="Delete"
                      className="rounded px-2 py-1 text-faint transition-colors hover:bg-crit/10 hover:text-crit"
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <input
                  defaultValue={log.notes || ""}
                  placeholder="Add a note (e.g. replaced bearing, reset relief valve)…"
                  onBlur={(e) => saveNote(log, e.target.value)}
                  className="mt-3 w-full rounded border border-hair bg-panel2 px-3 py-1.5 text-sm text-fg placeholder:text-faint outline-none focus:border-faint"
                />
              </li>
            );
          })}
          {logs.length === 0 && (
            <li className="px-5 py-8 text-center text-sm text-faint">
              No log entries yet. Save a recommendation from the AI Copilot.
            </li>
          )}
        </ul>
      </Card>
    </div>
  );
}
