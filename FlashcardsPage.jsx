import React, { useEffect, useState } from "react";
import { api } from "../utils/api";
import { BackButton, ProgressBar, Spinner, StatCard } from "../components/UI";

const SUBJECT_NAMES = { f1: "F1 — Business & Technology", f3: "F3 — Financial Accounting", fm: "Financial Markets", macro: "Macroeconomics" };

export default function ProgressPage({ navigate, subjectKey }) {
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getProgress(subjectKey)
      .then(setProgress)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [subjectKey]);

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
      <Spinner size={40} />
    </div>
  );

  const hasProgress = progress && progress.tests > 0;

  return (
    <div style={{ padding: "20px 16px" }}>
      <BackButton onClick={() => navigate("subject", { subjectKey })} />
      <div style={{ fontSize: 36, marginBottom: 10 }}>📊</div>
      <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>My Progress</h1>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 24 }}>
        {SUBJECT_NAMES[subjectKey]}
      </p>

      {!hasProgress ? (
        <div style={{
          background: "var(--card-bg)", border: "1px solid var(--card-border)",
          borderRadius: "var(--radius-lg)", padding: 32, textAlign: "center",
        }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📝</div>
          <p style={{ fontWeight: 600, marginBottom: 6 }}>No tests yet</p>
          <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>Take a practice test to see your progress here.</p>
        </div>
      ) : (
        <>
          {/* Stats grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 20 }}>
            <StatCard icon="✏️" label="Tests taken" value={progress.tests} />
            <StatCard icon="⭐" label="Best score" value={`${progress.best}%`} />
            <StatCard icon="📈" label="Avg score" value={`${progress.avg}%`} />
            <StatCard icon="🃏" label="Cards studied" value={progress.cards} />
          </div>

          {/* Score bar */}
          <div style={{
            background: "var(--card-bg)", border: "1px solid var(--card-border)",
            borderRadius: "var(--radius-lg)", padding: "18px 20px", marginBottom: 16,
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>Best result</span>
              <span style={{ fontSize: 13, fontFamily: "var(--mono)", color: gradeColor(progress.best) }}>
                {progress.best}%
              </span>
            </div>
            <ProgressBar value={progress.best} max={100} color={gradeColor(progress.best)} />
            <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 8 }}>
              {progress.best >= 90 ? "🌟 Excellent!" : progress.best >= 70 ? "👍 Good!" : progress.best >= 50 ? "📚 Keep studying" : "💪 Don't give up!"}
            </p>
          </div>

          {/* Average */}
          <div style={{
            background: "var(--card-bg)", border: "1px solid var(--card-border)",
            borderRadius: "var(--radius-lg)", padding: "18px 20px",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>Average score</span>
              <span style={{ fontSize: 13, fontFamily: "var(--mono)", color: "var(--accent-bright)" }}>{progress.avg}%</span>
            </div>
            <ProgressBar value={progress.avg} max={100} color="var(--accent)" />
          </div>
        </>
      )}
    </div>
  );
}

function gradeColor(pct) {
  if (pct >= 90) return "var(--green)";
  if (pct >= 70) return "var(--accent-bright)";
  if (pct >= 50) return "var(--gold)";
  return "var(--red)";
}
