import React from "react";

const tabs = [
  { id: "home", icon: "🏠", label: "Home" },
  { id: "admin", icon: "⚙️", label: "Admin", adminOnly: true },
];

export default function BottomNav({ active, setActive, isAdmin }) {
  const visibleTabs = tabs.filter(t => !t.adminOnly || isAdmin);

  return (
    <nav style={{
      position: "fixed", bottom: 0, left: 0, right: 0,
      background: "rgba(11,22,41,0.95)",
      backdropFilter: "blur(20px)",
      borderTop: "1px solid var(--card-border)",
      display: "flex", justifyContent: "space-around",
      padding: "8px 0 max(8px, env(safe-area-inset-bottom))",
      zIndex: 100,
    }}>
      {visibleTabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => setActive(tab.id)}
          style={{
            flex: 1, background: "none", border: "none", cursor: "pointer",
            display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
            padding: "6px 0",
            transition: "opacity var(--transition)",
            opacity: active === tab.id ? 1 : 0.45,
          }}
        >
          <span style={{ fontSize: 22 }}>{tab.icon}</span>
          <span style={{
            fontSize: 11, fontWeight: active === tab.id ? 600 : 400,
            color: active === tab.id ? "var(--accent-bright)" : "var(--text-secondary)",
            fontFamily: "var(--font)",
          }}>{tab.label}</span>
          {active === tab.id && (
            <div style={{
              width: 20, height: 3, borderRadius: 2,
              background: "var(--accent)", marginTop: 1,
            }} />
          )}
        </button>
      ))}
    </nav>
  );
}
