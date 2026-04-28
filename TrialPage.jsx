import React, { useEffect, useState } from "react";
import { useApp } from "../App";
import { Card, Button, Badge } from "../components/UI";

export default function HomePage({ navigate }) {
  const { user, subjects, refreshSubjects } = useApp();
  const [animIn, setAnimIn] = useState(false);

  useEffect(() => {
    refreshSubjects();
    setTimeout(() => setAnimIn(true), 50);
  }, []);

  const ownedSubjects = subjects.filter(s => s.owned);
  const availableSubjects = subjects.filter(s => !s.owned);
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div style={{ padding: "20px 16px 8px", opacity: animIn ? 1 : 0, transition: "opacity 0.4s" }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "flex-start",
          marginBottom: 6,
        }}>
          <div>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 2 }}>
              {greeting}, {user?.first_name || "Student"} 👋
            </p>
            <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.6px" }}>
              Study Hub
            </h1>
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
              British Management University
            </p>
          </div>
          <div style={{
            width: 48, height: 48, borderRadius: 14,
            background: "linear-gradient(135deg, var(--accent) 0%, #2563eb 100%)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 24,
          }}>📚</div>
        </div>

        {/* Quick stats bar */}
        <div style={{
          display: "flex", gap: 10, marginTop: 16,
          padding: "12px 16px",
          background: "var(--card-bg)", border: "1px solid var(--card-border)",
          borderRadius: "var(--radius)",
        }}>
          <div style={{ flex: 1, textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: "var(--accent-bright)" }}>
              {ownedSubjects.length}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Subjects</div>
          </div>
          <div style={{ width: 1, background: "var(--white-10)" }} />
          <div style={{ flex: 1, textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: "var(--green)" }}>
              {subjects.length}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Available</div>
          </div>
          <div style={{ width: 1, background: "var(--white-10)" }} />
          <div style={{ flex: 1, textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: "var(--gold)" }}>BMU</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>University</div>
          </div>
        </div>
      </div>

      {/* Free Trial Banner */}
      <div
        onClick={() => navigate("trial", { subjectKey: subjects[0]?.key || "f1" })}
        style={{
          background: "linear-gradient(135deg, rgba(79,142,247,0.25) 0%, rgba(37,99,235,0.15) 100%)",
          border: "1px solid rgba(79,142,247,0.35)",
          borderRadius: "var(--radius-lg)",
          padding: "16px 20px",
          display: "flex", alignItems: "center", gap: 14,
          cursor: "pointer", marginBottom: 24,
          position: "relative", overflow: "hidden",
        }}
      >
        <div style={{ fontSize: 36 }}>🎯</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15 }}>Try a Free Quiz</div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
            3 questions · No login needed · See what's inside
          </div>
        </div>
        <div style={{ marginLeft: "auto", color: "var(--accent-bright)", fontSize: 20 }}>→</div>
      </div>

      {/* My Subjects */}
      {ownedSubjects.length > 0 && (
        <section style={{ marginBottom: 28 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <h2 style={{ fontSize: 17, fontWeight: 700 }}>📖 My Subjects</h2>
            <Badge color="green">{ownedSubjects.length} owned</Badge>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {ownedSubjects.map((s, i) => (
              <SubjectCard
                key={s.key} subject={s} owned
                onStudy={() => navigate("subject", { subjectKey: s.key })}
                delay={i * 60}
              />
            ))}
          </div>
        </section>
      )}

      {/* Available Subjects */}
      {availableSubjects.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <h2 style={{ fontSize: 17, fontWeight: 700 }}>🛒 Buy Access</h2>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {availableSubjects.map((s, i) => (
              <SubjectCard
                key={s.key} subject={s}
                onBuy={() => navigate("payment", { subjectKey: s.key })}
                onTrial={() => navigate("trial", { subjectKey: s.key })}
                delay={i * 60}
              />
            ))}
          </div>
        </section>
      )}

      {/* Help */}
      <div style={{
        textAlign: "center", padding: "16px",
        color: "var(--text-muted)", fontSize: 12,
      }}>
        Questions? Contact admin · Access opens within 30 min after payment
      </div>
    </div>
  );
}

function SubjectCard({ subject, owned, onStudy, onBuy, onTrial, delay = 0 }) {
  const subjectEmojis = { f1: "💼", f3: "📊", fm: "📈", macro: "🌍" };
  const emoji = subjectEmojis[subject.key] || "📘";

  return (
    <div style={{
      background: "var(--card-bg)",
      border: `1px solid ${owned ? "rgba(79,142,247,0.3)" : "var(--card-border)"}`,
      borderRadius: "var(--radius-lg)",
      padding: "16px 18px",
      animation: `slideUp 0.4s ease ${delay}ms both`,
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 12, flexShrink: 0,
          background: owned
            ? "linear-gradient(135deg, var(--accent) 0%, #2563eb 100%)"
            : "var(--white-10)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 20,
        }}>
          {emoji}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, lineHeight: 1.3 }}>{subject.name}</div>
          {owned ? (
            <Badge color="accent" style={{ marginTop: 6 }}>✓ Owned</Badge>
          ) : (
            <div style={{ fontSize: 13, color: "var(--gold)", fontWeight: 600, marginTop: 4 }}>
              {subject.price?.toLocaleString()} UZS
            </div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        {owned ? (
          <Button onClick={onStudy} style={{ flex: 1 }} small>
            Study Now →
          </Button>
        ) : (
          <>
            <Button onClick={onBuy} style={{ flex: 2 }} small>
              🛒 Buy Access
            </Button>
            <Button onClick={onTrial} variant="secondary" style={{ flex: 1 }} small>
              Try Free
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
