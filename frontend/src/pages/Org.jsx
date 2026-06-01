import { useEffect, useState } from "react";
import api from "../lib/api";
import { Badge, Button, Card, CardHeader, Input } from "../components/ui.jsx";

const ROLES = ["owner", "manager", "operator", "auditor"];

export default function Org() {
  const [org, setOrg] = useState(null);
  const [sites, setSites] = useState([]);
  const [members, setMembers] = useState([]);
  const [me, setMe] = useState(null);
  const [newSite, setNewSite] = useState({ name: "", region: "IN", location: "" });
  const [msg, setMsg] = useState("");

  const load = () => {
    api.get("/auth/me").then((r) => setMe(r.data));
    api.get("/org").then((r) => setOrg(r.data)).catch(() => {});
    api.get("/org/sites").then((r) => setSites(r.data)).catch(() => {});
    api.get("/org/members").then((r) => setMembers(r.data)).catch(() => {});
  };
  useEffect(load, []);

  const canManage = me && (me.role === "owner" || me.role === "manager");
  const isOwner = me && me.role === "owner";

  const addSite = async () => {
    setMsg("");
    try {
      await api.post("/org/sites", newSite);
      setNewSite({ name: "", region: "IN", location: "" });
      load();
    } catch (e) {
      setMsg(e.response?.data?.detail || "Failed");
    }
  };

  const setRole = async (id, role) => {
    try {
      await api.patch(`/org/members/${id}/role`, { role });
      load();
    } catch (e) {
      setMsg(e.response?.data?.detail || "Failed");
    }
  };

  return (
    <div>
      <div className="mb-5 flex items-baseline justify-between">
        <h1 className="mono text-xs font-semibold uppercase tracking-[0.18em] text-muted">
          Organization
        </h1>
        {me && <Badge kind="verdict" value="MONITOR">{me.role}</Badge>}
      </div>

      <Card className="mb-3">
        <CardHeader title="Organization" subtitle={org ? `${org.name} · ${org.country || "—"}` : "—"} />
        <div className="p-4 text-sm text-muted">
          You are signed in as <span className="mono text-fg">{me?.email}</span> with role{" "}
          <span className="mono text-fg">{me?.role}</span>. Roles gate who can modify data —
          <span className="mono"> auditor</span> is read-only.
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader title="Sites" subtitle="Plants within this organization" />
          <div className="p-4">
            {sites.length === 0 ? (
              <p className="text-sm text-muted">No sites yet.</p>
            ) : (
              <ul className="mb-3 space-y-1.5">
                {sites.map((s) => (
                  <li key={s.id} className="flex items-center justify-between border-b border-hair pb-1.5">
                    <span className="text-sm text-fg">{s.name}</span>
                    <span className="mono text-[11px] text-faint">{s.location || "—"} · {s.region}</span>
                  </li>
                ))}
              </ul>
            )}
            {canManage && (
              <div className="grid grid-cols-3 gap-2">
                <Input placeholder="Name" value={newSite.name} onChange={(e) => setNewSite({ ...newSite, name: e.target.value })} />
                <Input placeholder="Location" value={newSite.location} onChange={(e) => setNewSite({ ...newSite, location: e.target.value })} />
                <select
                  className="rounded border border-hair bg-panel2 px-3 py-2 text-sm text-fg outline-none focus:border-faint"
                  value={newSite.region}
                  onChange={(e) => setNewSite({ ...newSite, region: e.target.value })}
                >
                  {["IN", "ZA", "MY", "TH", "ID", "VN", "NG", "KE", "GLOBAL"].map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
                <Button className="col-span-3" onClick={addSite} disabled={!newSite.name}>Add site</Button>
              </div>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="Members" subtitle={isOwner ? "Owners can change roles" : "Read-only"} />
          <div className="p-4 space-y-2">
            {members.map((m) => (
              <div key={m.id} className="flex items-center justify-between border-b border-hair pb-2">
                <span className="text-sm text-fg">{m.email}</span>
                {isOwner ? (
                  <select
                    className="rounded border border-hair bg-panel2 px-2 py-1 text-xs text-fg outline-none focus:border-faint"
                    value={m.role}
                    onChange={(e) => setRole(m.id, e.target.value)}
                  >
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                ) : (
                  <Badge kind="verdict" value="MONITOR">{m.role}</Badge>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
      {msg && <p className="mono mt-3 text-[11px] text-crit">{msg}</p>}
    </div>
  );
}
