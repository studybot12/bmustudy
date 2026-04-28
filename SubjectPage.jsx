import React, { useEffect, useState } from "react";
import { api } from "../utils/api";
import { BackButton, Button, Spinner, Badge } from "../components/UI";
import { useApp } from "../App";

const SUBJECT_NAMES = { f1: "F1 — Business & Technology", f3: "F3 — Financial Accounting", fm: "Financial Markets", macro: "Macroeconomics" };

export default function TrialPage({ navigate, subjectKey: initialKey }) {
  const { subjects } = useApp();
  const [selectedKey, setSelectedKey] = useState(initialKey || null);
  const [questions, setQuestions] = useState([]);
  const [index, setIndex] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [selected, setSelected] = useState(null);
  const [score, setScore] = useState(0);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);

  const startTrial = async (key) => {
    setLoading(true);
    setSelectedKey(key);
    try {
      const qs = await api.getTrialQuiz(key);
      setQuestions(qs);
      setStarted(true);
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    if (initialKey) startTrial(initialKey);
  }, []);

  const handleAnswer = (i) => {
    if (answered) return;
    setSelected(i);
    setAnswered(true);
    if (i === questions[index].correct) setScore(s => s + 1);
  };

  const handleNext = () => {
    if (index + 1 >= questions.length) {
      setDone(true);
    } else {
      setIndex(i => i + 1);
      setSelected(null);
      setAnswered(false);
    }
  };

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
      <Spinner size={40} />
    </div>
  );

  // Subject selector
  if (!started) {
    return (
      <div style={{ padding: "20px 16px" }}>
        <BackButton onClick={() => navigate("home")} />
        <div style={{ fontSize: 36, marginBottom: 10 }}>🎯</div>
        <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 6 }}>Free Trial Quiz</h1>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 24 }}>
          Try 3 questions from any subject — no payment required.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {Object.entries(SUBJECT_NAMES).map(([key, name]) => (
            <button
              key={key}
              onClick={() => startTrial(key)}
              style={{
                background: "var(--card-bg)", border: "1px solid var(--card-border)",
                borderRadius: "var(--radius-lg)", padding: "16px 18px",
                cursor: "pointer", textAlign: "left",
                display: "flex", alignItems: "center", gap: 14,
                color: "var(--text-primary)", fontFamily: "var(--font)",
              }}
            >
              <span style={{ fontSize: 24 }}>{"💼📊📈🌍".split("")[Object.keys(SUBJECT_NAMES).indexOf(key)]}</span>
              <span style={{ flex: 1, fontWeight: 600, fontSize: 14 }}>{name}</span>
              <span style={{ color: "var(--text-muted)" }}>→</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (done) {
    const notOwned = !subjects.find(s => s.key === selectedKey)?.owned;
    return (
      <div style={{ padding: 24, display: "flex", flexDirection: "column", alignItems: "center", gap: 18, marginTop: 40 }}>
        <div style={{ fontSize: 56 }}>🏁</div>
        <h2 style={{ fontSize: 24, fontWeight: 800 }}>Trial Complete!</h2>
        <div style={{
          background: "var(--card-bg)", border: "1px solid var(--card-border)",
          borderRadius: "var(--radius-lg)", padding: 20, width: "100%", textAlign: "center",
        }}>
          <div style={{ fontSize: 40, fontWeight: 800, color: "var(--accent-bright)" }}>{score}/3</div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
            {score === 3 ? "Perfect score! 🌟" : score >= 2 ? "Great job!" : "Keep practicing!"}
          </div>
        </div>

        {notOwned && (
          <div style={{
            background: "linear-gradient(135deg, rgba(79,142,247,0.2) 0%, rgba(37,99,235,0.12) 100%)",
            border: "1px solid rgba(79,142,247,0.35)",
            borderRadius: "var(--radius-lg)", padding: 18, width: "100%",
          }}>
            <p style={{ fontWeight: 700, marginBottom: 8 }}>💡 Liked it? Full version includes:</p>
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: 4 }}>
              {["✏️ 20 MCQ questions", "📖 Full study notes", "🃏 Flashcards", "📊 Progress tracking"].map(item => (
                <li key={item} style={{ fontSize: 13, color: "var(--text-secondary)" }}>{item}</li>
              ))}
            </ul>
            <Button onClick={() => navigate("payment", { subjectKey: selectedKey })} style={{ width: "100%", marginTop: 14 }}>
              🛒 Buy Full Access
            </Button>
          </div>
        )}

        <Button onClick={() => navigate("home")} variant="secondary" style={{ width: "100%" }}>← Back Home</Button>
      </div>
    );
  }

  const q = questions[index];
  const labels = ["A", "B", "C", "D"];

  return (
    <div style={{ padding: "20px 16px" }}>
      <BackButton onClick={() => navigate("home")} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <Badge color="gold">FREE TRIAL</Badge>
          <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
            {SUBJECT_NAMES[selectedKey]}
          </p>
        </div>
        <span style={{ fontFamily: "var(--mono)", color: "var(--text-muted)", fontSize: 13 }}>
          {index + 1}/3
        </span>
      </div>

      <div style={{
        background: "var(--card-bg)", border: "1px solid var(--card-border)",
        borderRadius: "var(--radius-lg)", padding: 20, marginBottom: 14,
      }}>
        <p style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.5 }}>{q?.question}</p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 14 }}>
        {q?.options?.map((opt, i) => {
          let bg = "var(--card-bg)", border = "var(--card-border)", color = "var(--text-primary)";
          if (answered) {
            if (i === q.correct) { bg = "rgba(52,209,157,0.12)"; border = "rgba(52,209,157,0.5)"; color = "var(--green)"; }
            else if (i === selected) { bg = "rgba(247,90,90,0.1)"; border = "rgba(247,90,90,0.4)"; color = "var(--red)"; }
          }
          return (
            <button key={i} onClick={() => handleAnswer(i)} disabled={answered} style={{
              background: bg, border: `1px solid ${border}`, borderRadius: "var(--radius)",
              padding: "13px 16px", cursor: answered ? "default" : "pointer",
              textAlign: "left", color, fontFamily: "var(--font)", fontSize: 14,
              display: "flex", alignItems: "center", gap: 12,
            }}>
              <span style={{
                width: 26, height: 26, borderRadius: 8, background: "var(--white-10)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 11, fontWeight: 700, fontFamily: "var(--mono)",
              }}>{labels[i]}</span>
              {opt}
            </button>
          );
        })}
      </div>

      {answered && (
        <Button onClick={handleNext} style={{ width: "100%" }}>
          {index + 1 >= 3 ? "🏁 See Results" : "Next →"}
        </Button>
      )}
    </div>
  );
}
