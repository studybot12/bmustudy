import React from "react";

export function Card({ children, style, onClick, glow }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--card-bg)",
        border: "1px solid var(--card-border)",
        borderRadius: "var(--radius-lg)",
        padding: 20,
        cursor: onClick ? "pointer" : "default",
        transition: "all var(--transition)",
        ...(glow && { boxShadow: "0 0 0 1px var(--accent-glow), 0 8px 32px rgba(0,0,0,0.3)" }),
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export function Button({ children, onClick, variant = "primary", style, disabled, small }) {
  const base = {
    border: "none", cursor: disabled ? "not-allowed" : "pointer",
    fontFamily: "var(--font)", fontWeight: 600,
    borderRadius: "var(--radius)",
    transition: "all var(--transition)",
    outline: "none",
    opacity: disabled ? 0.5 : 1,
    fontSize: small ? 13 : 15,
    padding: small ? "10px 18px" : "14px 24px",
    display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8,
  };

  const variants = {
    primary: {
      background: "linear-gradient(135deg, var(--accent) 0%, #2563eb 100%)",
      color: "#fff",
      boxShadow: "0 4px 20px rgba(79,142,247,0.35)",
    },
    secondary: {
      background: "var(--card-bg)",
      color: "var(--text-primary)",
      border: "1px solid var(--card-border)",
    },
    ghost: {
      background: "transparent",
      color: "var(--accent-bright)",
    },
    danger: {
      background: "rgba(247,90,90,0.15)",
      color: "var(--red)",
      border: "1px solid rgba(247,90,90,0.3)",
    },
    success: {
      background: "rgba(52,209,157,0.15)",
      color: "var(--green)",
      border: "1px solid rgba(52,209,157,0.3)",
    },
  };

  return (
    <button onClick={!disabled ? onClick : undefined} style={{ ...base, ...variants[variant], ...style }}>
      {children}
    </button>
  );
}

export function Badge({ children, color = "accent" }) {
  const colors = {
    accent: { bg: "rgba(79,142,247,0.15)", text: "var(--accent-bright)" },
    gold: { bg: "var(--gold-dim)", text: "var(--gold)" },
    green: { bg: "rgba(52,209,157,0.12)", text: "var(--green)" },
    red: { bg: "rgba(247,90,90,0.12)", text: "var(--red)" },
  };
  const c = colors[color] || colors.accent;
  return (
    <span style={{
      background: c.bg, color: c.text,
      padding: "3px 10px", borderRadius: 99,
      fontSize: 11, fontWeight: 600, letterSpacing: "0.4px",
    }}>
      {children}
    </span>
  );
}

export function BackButton({ onClick, label = "Back" }) {
  return (
    <button onClick={onClick} style={{
      background: "none", border: "none", cursor: "pointer",
      color: "var(--text-secondary)", fontFamily: "var(--font)",
      fontSize: 14, display: "flex", alignItems: "center", gap: 6,
      padding: "8px 0", marginBottom: 8,
    }}>
      <span style={{ fontSize: 18 }}>←</span> {label}
    </button>
  );
}

export function PageHeader({ title, subtitle, emoji }) {
  return (
    <div style={{ marginBottom: 24 }}>
      {emoji && <div style={{ fontSize: 36, marginBottom: 10 }}>{emoji}</div>}
      <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.5px", color: "var(--text-primary)" }}>
        {title}
      </h1>
      {subtitle && (
        <p style={{ fontSize: 14, color: "var(--text-secondary)", marginTop: 4 }}>{subtitle}</p>
      )}
    </div>
  );
}

export function Divider() {
  return <div style={{ height: 1, background: "var(--white-10)", margin: "16px 0" }} />;
}

export function Spinner({ size = 28 }) {
  return (
    <div style={{
      width: size, height: size,
      border: `2px solid var(--white-10)`,
      borderTopColor: "var(--accent)",
      borderRadius: "50%",
      animation: "spin 0.75s linear infinite",
      flexShrink: 0,
    }} />
  );
}

export function ProgressBar({ value, max, color = "var(--accent)" }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div style={{ position: "relative" }}>
      <div style={{
        height: 8, background: "var(--white-10)",
        borderRadius: 99, overflow: "hidden",
      }}>
        <div style={{
          height: "100%", width: `${pct}%`,
          background: color,
          borderRadius: 99,
          transition: "width 0.6s ease",
        }} />
      </div>
    </div>
  );
}

export function StatCard({ icon, label, value, sub }) {
  return (
    <div style={{
      background: "var(--card-bg)", border: "1px solid var(--card-border)",
      borderRadius: "var(--radius)", padding: "16px 18px",
      display: "flex", flexDirection: "column", gap: 4,
    }}>
      <div style={{ fontSize: 22 }}>{icon}</div>
      <div style={{ fontSize: 26, fontWeight: 800, color: "var(--accent-bright)", letterSpacing: "-0.5px" }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{sub}</div>}
    </div>
  );
}
