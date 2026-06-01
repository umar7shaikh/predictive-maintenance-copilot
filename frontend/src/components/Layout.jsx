import { NavLink, Outlet } from "react-router-dom";
import clsx from "clsx";
import { useAuth } from "../lib/auth.jsx";

const links = [
  { to: "/", label: "Fleet", end: true },
  { to: "/upload", label: "Data" },
  { to: "/tuning", label: "Detection" },
  { to: "/carbon", label: "Carbon" },
  { to: "/reports", label: "Reports" },
  { to: "/assistant", label: "Copilot" },
  { to: "/logs", label: "Log" },
  { to: "/org", label: "Org" },
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
                  {l.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-xs text-faint">
            <span className="mono">{user?.email}</span>
            <span className="text-hair">|</span>
            <button onClick={logout} className="uppercase tracking-wider hover:text-fg">
              Sign&nbsp;out
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
