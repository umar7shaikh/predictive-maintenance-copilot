import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";
import { Badge, Button, Card, CardHeader } from "../components/ui.jsx";

function statusTone(s) {
  if (s === "completed") return "green";
  if (s === "failed") return "red";
  return "yellow";
}

const FILE_INPUT =
  "block w-full text-sm text-muted file:mr-3 file:rounded file:border file:border-hair file:bg-panel2 file:px-3 file:py-2 file:text-fg hover:file:border-faint";

export default function Upload() {
  const [datasets, setDatasets] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [busy, setBusy] = useState(false);
  const csvRef = useRef();
  const pdfRef = useRef();
  const navigate = useNavigate();

  function refresh() {
    api.get("/datasets").then((r) => setDatasets(r.data));
    api.get("/documents").then((r) => setDocuments(r.data));
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, []);

  async function upload(ref, url) {
    const file = ref.current.files[0];
    if (!file) return;
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.post(url, fd);
      ref.current.value = "";
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function remove(url, label) {
    if (!confirm(`Delete ${label}? This removes its data permanently.`)) return;
    await api.delete(url);
    refresh();
  }

  async function resetAll() {
    if (!confirm("Reset ALL data — every machine, dataset, manual, recommendation and log will be deleted. Continue?")) return;
    setBusy(true);
    try {
      await api.post("/admin/reset");
      refresh();
      navigate("/");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <h1 className="mono text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          Data&nbsp;Ingestion
        </h1>
        <Button variant="danger" onClick={resetAll} disabled={busy}>Reset all data</Button>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Sensor data · CSV" subtitle="timestamp, machine_id, temperature, pressure, vibration, rpm" />
          <form onSubmit={(e) => { e.preventDefault(); upload(csvRef, "/datasets/upload"); }} className="space-y-3 p-5">
            <input ref={csvRef} type="file" accept=".csv" className={FILE_INPUT} />
            <Button type="submit" disabled={busy}>Upload &amp; analyze</Button>
          </form>
          <List
            items={datasets}
            unit="rows"
            countKey="row_count"
            empty="No datasets yet."
            onDelete={(d) => remove(`/datasets/${d.id}`, d.filename)}
          />
        </Card>

        <Card>
          <CardHeader title="Maintenance manual · PDF" subtitle="Embedded for grounded, cited AI answers" />
          <form onSubmit={(e) => { e.preventDefault(); upload(pdfRef, "/documents/upload"); }} className="space-y-3 p-5">
            <input ref={pdfRef} type="file" accept=".pdf" className={FILE_INPUT} />
            <Button type="submit" disabled={busy}>Upload &amp; embed</Button>
          </form>
          <List
            items={documents}
            unit="chunks"
            countKey="chunk_count"
            empty="No manuals yet."
            onDelete={(d) => remove(`/documents/${d.id}`, d.filename)}
          />
        </Card>
      </div>
    </div>
  );
}

function List({ items, unit, countKey, empty, onDelete }) {
  return (
    <ul className="border-t border-hair text-sm">
      {items.map((d) => (
        <li key={d.id} className="flex items-center justify-between gap-3 px-5 py-2">
          <span className="mono min-w-0 flex-1 truncate text-fg">{d.filename}</span>
          <span className="mono flex shrink-0 items-center gap-2 text-faint">
            {d[countKey] > 0 && <span>{d[countKey]} {unit}</span>}
            <Badge kind="health" value={statusTone(d.status)}>{d.status}</Badge>
            <button
              onClick={() => onDelete(d)}
              title="Delete"
              className="rounded px-1.5 text-faint transition-colors hover:bg-crit/10 hover:text-crit"
            >
              ✕
            </button>
          </span>
        </li>
      ))}
      {items.length === 0 && <li className="px-5 py-3 text-faint">{empty}</li>}
    </ul>
  );
}
