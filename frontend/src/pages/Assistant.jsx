import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../lib/api";
import { Badge, Button, Card, CardHeader, Input } from "../components/ui.jsx";

export default function Assistant() {
  const [params] = useSearchParams();
  const [machines, setMachines] = useState([]);
  const [machineId, setMachineId] = useState(params.get("machine") || "");
  const [question, setQuestion] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [lastRec, setLastRec] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const endRef = useRef();

  useEffect(() => {
    api.get("/machines").then((r) => setMachines(r.data));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function ask(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setSaved(false);
    const q = question;
    setMessages((m) => [...m, { role: "user", content: q }]);
    setQuestion("");
    try {
      const r = await api.post("/recommend", {
        machine_id: machineId ? Number(machineId) : null,
        question: q,
        session_id: sessionId,
        use_manuals: true,
      });
      setSessionId(r.data.session_id);
      setLastRec(r.data);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: r.data.explanation, verdict: r.data.verdict, citations: r.data.citations },
      ]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", content: "Request failed. Is the backend running?" }]);
    } finally {
      setBusy(false);
    }
  }

  async function saveToLog() {
    if (!lastRec) return;
    await api.post("/logs", { recommendation_id: lastRec.id, machine_id: lastRec.machine_id });
    setSaved(true);
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <Card className="flex h-[72vh] flex-col">
          <CardHeader
            title="AI Maintenance Copilot"
            subtitle="Grounded in anomaly data + uploaded manuals"
            right={
              <select
                value={machineId}
                onChange={(e) => setMachineId(e.target.value)}
                className="mono rounded border border-hair bg-panel2 px-2 py-1 text-xs text-fg"
              >
                <option value="">All machines</option>
                {machines.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            }
          />
          <div className="flex-1 space-y-3 overflow-auto p-5">
            {messages.length === 0 && (
              <p className="text-sm text-faint">
                Ask “Is PUMP-001 safe to keep running?” or “What does the manual say about high vibration?”
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "text-right" : ""}>
                <div
                  className={`inline-block max-w-[85%] rounded-md px-3 py-2 text-left text-sm ${
                    m.role === "user" ? "bg-fg text-base" : "border border-hair bg-panel2 text-fg"
                  }`}
                >
                  {m.role === "assistant" && m.verdict && (
                    <div className="mb-1.5"><Badge kind="verdict" value={m.verdict} /></div>
                  )}
                  <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                  {m.citations?.length > 0 && (
                    <div className="mt-2 space-y-1 border-t border-hair pt-2 text-xs text-muted">
                      {m.citations.map((c, j) => (
                        <p key={j}>
                          <span className="mono text-faint">[{c.source}{c.page ? `, p.${c.page}` : ""}]</span>{" "}
                          {c.snippet?.slice(0, 140)}…
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={endRef} />
          </div>
          <form onSubmit={ask} className="flex gap-2 border-t border-hair p-4">
            <Input placeholder="Ask about a machine's health or the manual…" value={question} onChange={(e) => setQuestion(e.target.value)} />
            <Button type="submit" disabled={busy}>{busy ? "…" : "Ask"}</Button>
          </form>
        </Card>
      </div>

      <div>
        <Card>
          <CardHeader title="Latest recommendation" />
          <div className="space-y-3 p-5 text-sm">
            {lastRec ? (
              <>
                <Badge kind="verdict" value={lastRec.verdict} />
                <p className="leading-relaxed text-muted">{lastRec.explanation}</p>
                <Button onClick={saveToLog} variant="ghost" disabled={saved} className="w-full">
                  {saved ? "Saved to log ✓" : "Save to maintenance log"}
                </Button>
              </>
            ) : (
              <p className="text-faint">No recommendation yet.</p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
