import React, { useEffect, useState } from "react";
import { api } from "../utils/api";
import { BackButton, Button, ProgressBar, Spinner } from "../components/UI";

export default function QuizPage({ navigate, subjectKey }) {
  const [questions, setQuestions] = useState([]);
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState(null);
  const [answered, setAnswered] = useState(false);
  const [score, setScore] = useState(0);
  const [loading, setLoading] = useState(true);
  const [done, setDone] = useState(false);
  const [explanation, setExplanation] = useState("");

  useEffect(() => {
    api.getQuiz(subjectKey)
      .then(setQuestions)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [subjectKey]);

  const handleAnswer = async (optionIdx) => {
    if (answered) return;
    setSelected(optionIdx);
    setAnswered(true);

    // Fetch explanation from server
    try {
      const res = await api.checkAnswer ? null : null; // using local check
      const q = questions[index];
      const isCorrect = optionIdx === q.correct;
      if (isCorrect) setScore(s => s + 1);
      // We rely on the question having an explanation key (not passed from server in safe mode)
      // Show generic feedback
      setExplanation(isCorrect ? "✅ Correct!" : `❌ Correct answer: ${q.options[q.correct]}`);
    } catch {}
  };

  const handleNext = () => {
    if (index + 1 >= questions.length) {
      api.submitQuiz(subjectKey, score + (selected === questions[index].correct ? 1 : 0), questions.length)
        .catch(() => {});
      setDone(true);
    } else {
      setIndex(i => i + 1);
      setSelected(null);
      setAnswered(false);
      setExplanation("");
    }
  };

  const restart = () => {
    api.getQuiz(subjectKey).then(q => { setQuestions(q); setIndex(0); setSelected(null); setAnswered(false); setScore(0); setDone(false); setExplanation(""); }).catch(() => {});
  };

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
      <Spinner size={40} />
    </div>
  );

  if (done) {
    const total = questions.length;
    const pct = Math.round(score / total * 100);
    const gradeEmoji = pct >= 90 ? "🌟" : pct >= 70 ? "👍" : pct >= 50 ? "📚" : "💪";
    const gradeText = pct >= 90 ? "Excellent! Ready for the exam!" : pct >= 70 ? "Good job! Review weak areas." : pct >= 50 ? "Keep studying!" : "Don't give up, try again!";

    return (
      <div style={{ padding: 24, display: "flex", flexDirection: "column", alignItems: "center", gap: 20, marginTop: 40 }}>
        <div style={{ fontSize: 64 }}>{gradeEmoji}</div>
        <h2 style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.5px" }}>{score}/{total}</h2>
        <div style={{
          background: "var(--card-bg)", border: "1px solid var(--card-border)",
          borderRadius: "var(--radius-lg)", padding: "20px", width: "100%", textAlign: "center",
        }}>
          <div style={{ fontSize: 36, fontWeight: 800, color: pct >= 70 ? "var(--green)" : "var(--red)", marginBottom: 6 }}>
            {pct}%
          </div>
          <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>{gradeText}</div>
        </div>
        <Button onClick={restart} style={{ width: "100%" }}>🔄 New Quiz</Button>
        <Button onClick={() => navigate("subject", { subjectKey })} variant="secondary" style={{ width: "100%" }}>
          ← Back to Subject
        </Button>
      </div>
    );
  }

  const q = questions[index];
  const optionLabels = ["A", "B", "C", "D"];

  return (
    <div style={{ padding: "20px 16px" }}>
      <BackButton onClick={() => navigate("subject", { subjectKey })} />

      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>✏️ Practice Test</span>
          <span style={{ fontSize: 13, fontFamily: "var(--mono)", color: "var(--text-muted)" }}>
            {index + 1}/{questions.length}
          </span>
        </div>
        <ProgressBar value={index} max={questions.length} />
      </div>

      {/* Question */}
      <div style={{
        background: "var(--card-bg)",
        border: "1px solid var(--card-border)",
        borderRadius: "var(--radius-lg)",
        padding: "20px", marginBottom: 16,
        animation: "fadeIn 0.25s ease",
        key: index,
      }}>
        <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8, fontFamily: "var(--mono)" }}>
          Q{index + 1}
        </div>
        <p style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.5 }}>{q?.question}</p>
      </div>

      {/* Options */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
        {q?.options?.map((opt, i) => {
          let bg = "var(--card-bg)";
          let border = "var(--card-border)";
          let textColor = "var(--text-primary)";

          if (answered) {
            if (i === q.correct) { bg = "rgba(52,209,157,0.12)"; border = "rgba(52,209,157,0.5)"; textColor = "var(--green)"; }
            else if (i === selected && i !== q.correct) { bg = "rgba(247,90,90,0.1)"; border = "rgba(247,90,90,0.4)"; textColor = "var(--red)"; }
          } else if (selected === i) {
            bg = "rgba(79,142,247,0.15)"; border = "rgba(79,142,247,0.5)";
          }

          return (
            <button
              key={i}
              onClick={() => handleAnswer(i)}
              disabled={answered}
              style={{
                background: bg, border: `1px solid ${border}`,
                borderRadius: "var(--radius)", padding: "13px 16px",
                cursor: answered ? "default" : "pointer",
                textAlign: "left", color: textColor,
                fontFamily: "var(--font)", fontSize: 14,
                display: "flex", alignItems: "center", gap: 12,
                transition: "all 0.15s",
              }}
            >
              <span style={{
                width: 26, height: 26, borderRadius: 8, flexShrink: 0,
                background: answered && i === q.correct ? "var(--green)" : "var(--white-10)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 11, fontWeight: 700, fontFamily: "var(--mono)",
                color: answered && i === q.correct ? "#fff" : "var(--text-secondary)",
              }}>
                {optionLabels[i]}
              </span>
              {opt}
            </button>
          );
        })}
      </div>

      {/* Feedback */}
      {answered && explanation && (
        <div style={{
          background: "rgba(255,255,255,0.04)", border: "1px solid var(--white-10)",
          borderRadius: "var(--radius)", padding: "12px 14px",
          fontSize: 13, color: "var(--text-secondary)", marginBottom: 14,
          animation: "fadeIn 0.2s ease",
        }}>
          {explanation}
        </div>
      )}

      {answered && (
        <Button onClick={handleNext} style={{ width: "100%" }}>
          {index + 1 >= questions.length ? "🏁 See Results" : "Next Question →"}
        </Button>
      )}
    </div>
  );
}
