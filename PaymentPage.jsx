import React, { useEffect, useState } from "react";
import { api } from "../utils/api";
import { Button, Spinner, StatCard, Divider, Badge } from "../components/UI";
import { useApp } from "../App";

export default function AdminPage({ navigate }) {
  const { user } = useApp();
  const [tab, setTab] = useState("stats");
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [promoCode, setPromoCode] = useState("");
  const [promoDiscount, setPromoDiscount] = useState("");
  const [promoMsg, setPromoMsg] = useState("");

  // Grant modal
  const [grantUser, setGrantUser] = useState("");
  const [grantSubject, setGrantSubject] = useState("");
  const [grantMsg, setGrantMsg] = useState("");

  useEffect(() => {
    if (!user?.is_admin) return;
    Promise.all([api.getAdminStats(), api.getAdminUsers(), api.getAdminSubjects()])
      .then(([s, u, sub]) => { setStats(s); setUsers(u); setSubjects(sub); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (!user?.is_admin) return (
    <div style={{ padding: 24, textAlign: "center", marginTop: 60 }}>
      <div style={{ fontSize: 48 }}>🔒</div>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginTop: 12 }}>Admin Only</h2>
    </div>
  );

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
      <Spinner size={40} />
    </div>
  );

  const handleAddPromo = async () => {
    if (!promoCode || !promoDiscount) return;
    try {
      await api.addPromo(promoCode.trim().toUpperCase(), parseInt(promoDiscount));
      setPromoMsg("✅ Promo added!");
      setPromoCode(""); setPromoDiscount("");
    } catch { setPromoMsg("❌ Error"); }
  };

  const handleGrant = async () => {
    if (!grantUser || !grantSubject) return;
    try {
      await api.grantAccess(parseInt(grantUser), grantSubject);
      setGrantMsg("✅ Access granted!");
    } catch { setGrantMsg("❌ Error"); }
  };

  const TABS = [
    { id: "stats", label: "📊 Stats" },
    { id: "users", label: "👥 Users" },
    { id: "tools", label: "🛠 Tools" },
  ];

  return (
    <div style={{ padding: "20px 16px" }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800 }}>⚙️ Admin Panel</h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>Study Hub BMU</p>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 20 }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            flex: 1, padding: "9px 6px", border: "none", cursor: "pointer",
            borderRadius: "var(--radius-sm)", fontFamily: "var(--font)", fontSize: 12, fontWeight: 600,
            background: tab === t.id ? "var(--accent)" : "var(--card-bg)",
            color: tab === t.id ? "#fff" : "var(--text-secondary)",
            transition: "all 0.15s",
          }}>{t.label}</button>
        ))}
      </div>

      {/* Stats Tab */}
      {tab === "stats" && stats && (
        <div style={{ animation: "fadeIn 0.3s ease" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 20 }}>
            <StatCard icon="👥" label="Total students" value={stats.users} />
            <StatCard icon="💰" label="Paid accesses" value={stats.paid} />
            <StatCard icon="💵" label="Revenue" value={`${(stats.revenue || 0).toLocaleString()}`} sub="UZS" />
            <StatCard icon="📘" label="Subjects" value={Object.keys(stats.by_subject || {}).length} />
          </div>

          <div style={{
            background: "var(--card-bg)", border: "1px solid var(--card-border)",
            borderRadius: "var(--radius-lg)", padding: "18px 20px",
          }}>
            <p style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>📘 By Subject</p>
            {Object.entries(stats.by_subject || {}).map(([key, count]) => (
              <div key={key} style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{key}</span>
                <Badge color="accent">{count} students</Badge>
              </div>
            ))}
            {Object.keys(stats.by_subject || {}).length === 0 && (
              <p style={{ fontSize: 13, color: "var(--text-muted)" }}>No paid accesses yet</p>
            )}
          </div>
        </div>
      )}

      {/* Users Tab */}
      {tab === "users" && (
        <div style={{ animation: "fadeIn 0.3s ease" }}>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 12 }}>{users.length} total users</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {users.map(u => (
              <div key={u.user_id} style={{
                background: "var(--card-bg)", border: "1px solid var(--card-border)",
                borderRadius: "var(--radius)", padding: "14px 16px",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{u.first_name || "User"}</div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)", fontFamily: "var(--mono)" }}>
                      {u.username ? `@${u.username}` : `ID: ${u.user_id}`}
                    </div>
                  </div>
                  {u.subjects.length > 0 && <Badge color="green">{u.subjects.length} subjects</Badge>}
                </div>
                {u.subjects.length > 0 && (
                  <div style={{ display: "flex", gap: 4, marginTop: 8, flexWrap: "wrap" }}>
                    {u.subjects.map(s => <Badge key={s} color="accent">{s}</Badge>)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tools Tab */}
      {tab === "tools" && (
        <div style={{ animation: "fadeIn 0.3s ease", display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Manual grant */}
          <div style={{
            background: "var(--card-bg)", border: "1px solid var(--card-border)",
            borderRadius: "var(--radius-lg)", padding: "18px 20px",
          }}>
            <p style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>🔓 Grant Access</p>
            <input
              value={grantUser} onChange={e => setGrantUser(e.target.value)}
              placeholder="User ID"
              style={inputStyle}
            />
            <select
              value={grantSubject} onChange={e => setGrantSubject(e.target.value)}
              style={{ ...inputStyle, marginTop: 8 }}
            >
              <option value="">Select subject...</option>
              {subjects.map(s => <option key={s.key} value={s.key}>{s.name}</option>)}
            </select>
            <Button onClick={handleGrant} style={{ width: "100%", marginTop: 10 }} small>
              Grant Access
            </Button>
            {grantMsg && <p style={{ fontSize: 12, marginTop: 6, color: grantMsg.startsWith("✅") ? "var(--green)" : "var(--red)" }}>{grantMsg}</p>}
          </div>

          <Divider />

          {/* Add promo */}
          <div style={{
            background: "var(--card-bg)", border: "1px solid var(--card-border)",
            borderRadius: "var(--radius-lg)", padding: "18px 20px",
          }}>
            <p style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>🎁 Add Promo Code</p>
            <input
              value={promoCode} onChange={e => setPromoCode(e.target.value.toUpperCase())}
              placeholder="PROMO CODE"
              style={inputStyle}
            />
            <input
              value={promoDiscount} onChange={e => setPromoDiscount(e.target.value)}
              placeholder="Discount % (e.g. 20)"
              type="number" min="1" max="100"
              style={{ ...inputStyle, marginTop: 8 }}
            />
            <Button onClick={handleAddPromo} style={{ width: "100%", marginTop: 10 }} small>
              Add Promo
            </Button>
            {promoMsg && <p style={{ fontSize: 12, marginTop: 6, color: promoMsg.startsWith("✅") ? "var(--green)" : "var(--red)" }}>{promoMsg}</p>}
          </div>
        </div>
      )}
    </div>
  );
}

const inputStyle = {
  width: "100%", background: "rgba(255,255,255,0.05)",
  border: "1px solid var(--card-border)", borderRadius: "var(--radius-sm)",
  padding: "10px 14px", color: "var(--text-primary)",
  fontFamily: "var(--font)", fontSize: 13, outline: "none",
  boxSizing: "border-box",
};
