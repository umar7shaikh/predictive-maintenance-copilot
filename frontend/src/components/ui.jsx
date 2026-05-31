import clsx from "clsx";

export function Card({ className, children }) {
  return (
    <div className={clsx("rounded-md border border-hair bg-panel", className)}>{children}</div>
  );
}

export function CardHeader({ title, subtitle, right }) {
  return (
    <div className="flex items-start justify-between border-b border-hair px-5 py-3">
      <div>
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-faint">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export function Button({ className, variant = "primary", ...props }) {
  const styles = {
    primary: "bg-fg text-base hover:bg-white",
    ghost: "border border-hair bg-panel2 text-fg hover:border-faint",
    danger: "bg-crit text-white hover:brightness-110",
  };
  return (
    <button
      className={clsx(
        "rounded px-3.5 py-2 text-sm font-medium transition-colors disabled:opacity-40",
        styles[variant],
        className
      )}
      {...props}
    />
  );
}

export function Input(props) {
  return (
    <input
      className="w-full rounded border border-hair bg-panel2 px-3 py-2 text-sm text-fg placeholder:text-faint outline-none focus:border-faint"
      {...props}
    />
  );
}

// --- status colors -------------------------------------------------
const HEALTH_DOT = { red: "bg-crit", yellow: "bg-warn", green: "bg-steel" };
const HEALTH_TEXT = { red: "text-crit", yellow: "text-warn", green: "text-steel" };
const HEALTH_LABEL = { red: "CRIT", yellow: "WARN", green: "OK" };

export function StatusDot({ health, pulse }) {
  return (
    <span className="relative inline-flex h-2.5 w-2.5">
      {pulse && health === "red" && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-crit opacity-60" />
      )}
      <span className={clsx("relative inline-flex h-2.5 w-2.5 rounded-full", HEALTH_DOT[health])} />
    </span>
  );
}

const SEVERITY = {
  HIGH: "border-crit/40 bg-crit/10 text-crit",
  MEDIUM: "border-warn/40 bg-warn/10 text-warn",
  MONITOR: "border-steel/40 bg-steel/10 text-steel",
};
const VERDICT = {
  URGENT_SERVICE: "border-crit/40 bg-crit/10 text-crit",
  SCHEDULE_SERVICE: "border-warn/40 bg-warn/10 text-warn",
  MONITOR: "border-steel/40 bg-steel/10 text-steel",
  SAFE: "border-hair bg-panel2 text-muted",
};
const HEALTH_BADGE = {
  red: "border-crit/40 bg-crit/10 text-crit",
  yellow: "border-warn/40 bg-warn/10 text-warn",
  green: "border-steel/40 bg-steel/10 text-steel",
};

export function Badge({ kind = "health", value, children }) {
  const maps = { health: HEALTH_BADGE, severity: SEVERITY, verdict: VERDICT };
  const cls = (maps[kind] || HEALTH_BADGE)[value] || "border-hair bg-panel2 text-muted";
  return (
    <span
      className={clsx(
        "mono inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider",
        cls
      )}
    >
      {children || value}
    </span>
  );
}

export { HEALTH_TEXT, HEALTH_LABEL };

// --- KPI stat tile -------------------------------------------------
export function Kpi({ label, value, accent, sub }) {
  return (
    <div className="rounded-md border border-hair bg-panel px-4 py-3">
      <div className={clsx("mono text-2xl font-semibold", accent || "text-fg")}>{value}</div>
      <div className="mt-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">
        {label}
      </div>
      {sub && <div className="mt-0.5 text-[11px] text-muted">{sub}</div>}
    </div>
  );
}

// --- inline SVG sparkline -----------------------------------------
export function Sparkline({ data = [], color = "#7c8694", width = 120, height = 30 }) {
  if (!data || data.length < 2) return <div style={{ width, height }} />;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const step = width / (data.length - 1);
  const pts = data
    .map((v, i) => `${(i * step).toFixed(1)},${(height - ((v - min) / span) * height).toFixed(1)}`)
    .join(" ");
  const lastX = width;
  const lastY = height - ((data[data.length - 1] - min) / span) * height;
  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
      <circle cx={lastX} cy={lastY} r="2" fill={color} />
    </svg>
  );
}
