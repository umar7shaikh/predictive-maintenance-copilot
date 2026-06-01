import { NavLink, Outlet } from "react-router-dom";
import clsx from "clsx";
import { useAuth } from "../lib/auth.jsx";
import { LANGUAGES, getLang, setLang, t } from "../lib/i18n.js";

const links = [
  { to: "/", key: "nav.fleet", end: true },
  { to: "/upload", key: "nav.data" },
  { to: "/tuning", key: "nav.detection" },
  { to: "/carbon", key: "nav.carbon" },
  { to: "/reports", key: "nav.reports" },
  { to: "/assistant", key: "nav.copilot" },
  { to: "/logs", key: "nav.log" },
  { to: "/org", key: "nav.org" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen bg-base bg-grid">
      <header className="sticky top-0 z-10 border-b border-hair bg-base/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-9">
            <div className="flex items-center gap-2.5">
              <span className="mono text-warn">▓</span>
              <span className="mono text-sm font-semibold tracking-[0.18em] text-fg">
                PDM&nbsp;COPILOT
              </span>
            </div>
            <nav className="flex gap-1">
              {links.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  end={l.end}
                  className={({ isActive }) =>
                    clsx(
                      "mono rounded px-3 py-1.5 text-xs uppercase tracking-[0.12em] transition-colors",
                      isActive ? "bg-panel2 text-fg" : "text-faint hover:text-fg"
                    )
                  }
                >
                  {t(l.key)}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-xs text-faint">
            <select
              value={getLang()}
              onChange={(e) => setLang(e.target.value)}
              className="mono rounded border border-hair bg-panel2 px-1.5 py-1 text-[11px] text-muted outline-none focus:border-faint"
              title="Language"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label}</option>
              ))}
            </select>
            <span className="mono">{user?.email}</span>
            <span className="text-hair">|</span>
            <button onClick={logout} className="uppercase tracking-wider hover:text-fg">
              {t("app.signout")}
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
