import React, { useEffect, useState } from "react";
import { api } from "../utils/api";
import { BackButton, Button, Spinner, ProgressBar } from "../components/UI";

export default function FlashcardsPage({ navigate, subjectKey }) {
  const [cards, setCards] = useState([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(true);
  const [done, setDone] = useState(false);

  useEffect(() => {
    api.getFlashcards(subjectKey)
      .then(setCards)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [subjectKey]);

  const handleNext = () => {
    api.markCardViewed(subjectKey).catch(() => {});
    setFlipped(false);
    setTimeout(() => {
      if (index + 1 >= cards.length) {
        setDone(true);
      } else {
        setIndex(i => i + 1);
      }
    }, 150);
  };

  const handlePrev = () => {
    if (index > 0) {
      setFlipped(false);
      setTimeout(() => setIndex(i => i - 1), 150);
    }
  };

  const restart = () => { setIndex(0); setFlipped(false); setDone(false); };

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
      <Spinner size={40} />
    </div>
  );

  if (done) return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", alignItems: "center", gap: 20, marginTop: 60 }}>
      <div style={{ fontSize: 60 }}>🎉</div>
      <h2 style={{ fontSize: 22, fontWeight: 800, textAlign: "center" }}>All {cards.length} Cards Done!</h2>
      <p style={{ color: "var(--text-secondary)", textAlign: "center" }}>Great work! You're one step closer to acing your exam.</p>
      <Button onClick={restart} style={{ width: "100%" }}>🔄 Review Again</Button>
      <Button onClick={() => navigate("subject", { subjectKey })} variant="secondary" style={{ width: "100%" }}>← Back to Subject</Button>
    </div>
  );

  const card = cards[index];

  return (
    <div style={{ padding: "20px 16px" }}>
      <BackButton onClick={() => navigate("subject", { subjectKey })} />

      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Flashcards</span>
          <span style={{ fontSize: 13, color: "var(--text-muted)", fontFamily: "var(--mono)" }}>
            {index + 1} / {cards.length}
          </span>
        </div>
        <ProgressBar value={index + 1} max={cards.length} />
      </div>

      {/* Flip Card */}
      <div
        onClick={() => setFlipped(f => !f)}
        style={{
          minHeight: 280, borderRadius: "var(--radius-xl)",
          cursor: "pointer",
          perspective: 1000,
          marginBottom: 20,
        }}
      >
        <div style={{
          position: "relative", width: "100%", minHeight: 280,
          transformStyle: "preserve-3d",
          transition: "transform 0.45s ease",
          transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)",
        }}>
          {/* Front */}
          <div style={{
            position: "absolute", inset: 0,
            backfaceVisibility: "hidden",
            background: "linear-gradient(135deg, rgba(79,142,247,0.2) 0%, rgba(37,99,235,0.1) 100%)",
            border: "1px solid rgba(79,142,247,0.3)",
            borderRadius: "var(--radius-xl)",
            padding: "32px 24px",
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            textAlign: "center", gap: 12,
          }}>
            <div style={{ fontSize: 28 }}>❓</div>
            <p style={{ fontSize: 17, fontWeight: 600, lineHeight: 1.5 }}>{card?.term}</p>
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>Tap to reveal answer</p>
          </div>

          {/* Back */}
          <div style={{
            position: "absolute", inset: 0,
            backfaceVisibility: "hidden",
            transform: "rotateY(180deg)",
            background: "linear-gradient(135deg, rgba(52,209,157,0.15) 0%, rgba(16,185,129,0.08) 100%)",
            border: "1px solid rgba(52,209,157,0.3)",
            borderRadius: "var(--radius-xl)",
            padding: "32px 24px",
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            textAlign: "center", gap: 12,
          }}>
            <div style={{ fontSize: 28 }}>💡</div>
            <p style={{ fontSize: 15, lineHeight: 1.6, color: "var(--text-primary)" }}>{card?.definition}</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div style={{ display: "flex", gap: 10 }}>
        <Button onClick={handlePrev} variant="secondary" disabled={index === 0} style={{ flex: 1 }}>
          ← Prev
        </Button>
        {flipped ? (
          <Button onClick={handleNext} style={{ flex: 2 }}>
            Next Card →
          </Button>
        ) : (
          <Button onClick={() => setFlipped(true)} variant="secondary" style={{ flex: 2 }}>
            👁 Show Answer
          </Button>
        )}
      </div>
    </div>
  );
}
