import type { Risk } from "../data";

// Status is always shown as icon + word, never color alone.
const ICONS: Record<Risk, JSX.Element> = {
  Low: <path d="M8 12.5l2.8 2.8L16 10" />,
  Minor: <path d="M12 7v6M12 16.5v.5" />,
  Moderate: <path d="M12 7v6M12 16.5v.5" />,
  Major: <path d="M9 9l6 6M15 9l-6 6" />,
};

export function StatusPill({ risk, size = "md" }: { risk: Risk; size?: "md" | "lg" }) {
  return (
    <span className={`pill pill-${risk.toLowerCase()} pill-${size}`}>
      <svg viewBox="0 0 24 24" aria-hidden="true" className="pill-icon">
        {risk === "Moderate" ? <path d="M12 3.5L22 20H2z" /> : <circle cx="12" cy="12" r="9" />}
        {ICONS[risk]}
      </svg>
      {risk} risk
    </span>
  );
}

export function StatusDot({ risk }: { risk: Risk }) {
  return <span className={`dot dot-${risk.toLowerCase()}`} aria-hidden="true" />;
}
