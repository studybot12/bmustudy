import React, { useEffect, useState } from "react";
import { api } from "../utils/api";
import { BackButton, Button, Card, ProgressBar } from "../components/UI";

const MODES = [
  { id: "materials", icon: "📖", title: "Study Notes", desc: "Full course notes by chapter", color: "#4f8ef7" },
  { id: "flashcards", icon: "🃏", title: "Flashcards", desc: "Key terms and definitions", color: "#a78bfa" },
  { id: "quiz", icon: "✏️", title: "Practice Test", desc: "20 MCQ questions", color: "#34d19d" },
  { id: "progress", icon: "📊", title: "My Progress", desc: "Stats and results", color: "#f5c842" },
];

const SUBJECT_EMOJIS = { f1: "💼", f3: "📊", fm: "📈", macro: "🌍" };

export default function SubjectPage({ navigate, subjectKey }) {
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    api.getProgress(subjectKey).then(setProgress).catch(() => {});
  }, [subjectKey]);

  const subjectNames = { f1: "F1 — Business & Technology", f3: "F3 — Financial Accounting", fm: "Financial Markets", macro: "Macroeconomics" };
  const name = subjectNames[subjectKey] || subjectKey;

  return (
    <div style={{ padding: "20px 16px" }}>
      <BackButton onClick={() => navigate("home")} />

      {/* Subject Header */}
      <div style={{
        background: "linear-gradient(135deg, rgba(79,142,247,0.2) 0%, rgba(37,99,235,0.1) 100%)",
        border: "1px solid rgba(79,142,247,0.25)",
        borderRadius: "var(--radius-xl)",
        padding: "24px 20px",
        marginBottom: 24,
        position: "relative", overflow: "hidden",
      }}>
        <div style={{ fontSize: 42, marginBottom: 10 }}>{SUBJECT_EMOJIS[subjectKey] || "📘"}</div>
        <h1 style={{ fontSize: 20, fontWeight: 800, letterSpacing: "-0.4px", lineHeight: 1.3 }}>{name}</h1>
        <p style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>Choose a study mode below</p>

        {/* Progress summary */}
        {progress && progress.tests > 0 && (
          <div style={{
            marginTop: 16, padding: "10px 14px",
            background: "rgba(255,255,255,0.07)", borderRadius: "var(--radius)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Best score</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--green)" }}>{progress.best}%</span>
            </div>
            <ProgressBar value={progress.best} max={100} color="var(--green)" />
          </div>
        )}
      </div>

      {/* Mode Cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {MODES.map((mode, i) => (
          <ModeCard
            key={mode.id}
            mode={mode}
            delay={i * 60}
            onClick={() => navigate(mode.id, { subjectKey })}
            stats={mode.id === "progress" && progress ? progress : null}
          />
        ))}
      </div>
    </div>
  );
}

function ModeCard({ mode, onClick, delay, stats }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--card-bg)",
        border: "1px solid var(--card-border)",
        borderRadius: "var(--radius-lg)",
        padding: "16px 18px",
        cursor: "pointer",
        animation: `slideUp 0.35s ease ${delay}ms both`,
        display: "flex", alignItems: "center", gap: 14,
        transition: "border-color 0.15s",
      }}
    >
      <div style={{
        width: 46, height: 46, borderRadius: 13, flexShrink: 0,
        background: `${mode.color}22`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 22,
      }}>
        {mode.icon}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 700, fontSize: 15 }}>{mode.title}</div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
          {stats && stats.tests > 0
            ? `${stats.tests} tests · avg ${stats.avg}% · best ${stats.best}%`
            : mode.desc}
        </div>
      </div>
      <span style={{ color: "var(--text-muted)", fontSize: 18 }}>→</span>
    </div>
  );
}
