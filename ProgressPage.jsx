import React, { useEffect, useState } from "react";
import { api } from "../utils/api";
import { BackButton, Spinner } from "../components/UI";

export default function MaterialsPage({ navigate, subjectKey }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [openChapter, setOpenChapter] = useState(0);

  useEffect(() => {
    api.getMaterials(subjectKey)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [subjectKey]);

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
      <Spinner size={40} />
    </div>
  );

  return (
    <div style={{ padding: "20px 16px" }}>
      <BackButton onClick={() => navigate("subject", { subjectKey })} />
      <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 6, letterSpacing: "-0.4px" }}>
        📖 Study Notes
      </h1>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 20 }}>
        {data?.name}
      </p>

      {/* Chapter list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {(data?.chapters || []).map((ch, i) => (
          <ChapterAccordion
            key={i}
            index={i}
            chapter={ch}
            isOpen={openChapter === i}
            onToggle={() => setOpenChapter(openChapter === i ? -1 : i)}
          />
        ))}
      </div>
    </div>
  );
}

function ChapterAccordion({ chapter, isOpen, onToggle, index }) {
  // Parse basic markdown-style formatting
  const renderContent = (text) => {
    return text.split("\n").map((line, i) => {
      if (line.startsWith("🔹") || line.startsWith("•") || line.startsWith("*")) {
        return <div key={i} style={{ marginBottom: 4, paddingLeft: line.startsWith("•") ? 12 : 0 }}>
          {formatLine(line)}
        </div>;
      }
      if (line.trim() === "") return <div key={i} style={{ height: 8 }} />;
      return <div key={i} style={{ marginBottom: 4 }}>{formatLine(line)}</div>;
    });
  };

  const formatLine = (line) => {
    const parts = line.split(/(\*[^*]+\*)/g);
    return parts.map((p, i) => {
      if (p.startsWith("*") && p.endsWith("*")) {
        return <strong key={i} style={{ color: "var(--accent-bright)" }}>{p.slice(1, -1)}</strong>;
      }
      return p;
    });
  };

  return (
    <div style={{
      background: "var(--card-bg)",
      border: `1px solid ${isOpen ? "rgba(79,142,247,0.35)" : "var(--card-border)"}`,
      borderRadius: "var(--radius-lg)",
      overflow: "hidden",
      transition: "border-color 0.2s",
    }}>
      <button
        onClick={onToggle}
        style={{
          width: "100%", background: "none", border: "none", cursor: "pointer",
          padding: "16px 18px", display: "flex", alignItems: "center", gap: 12,
          textAlign: "left",
        }}
      >
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: isOpen ? "var(--accent)" : "var(--white-10)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 12, fontWeight: 700, color: isOpen ? "#fff" : "var(--text-secondary)",
          flexShrink: 0, transition: "background 0.2s",
          fontFamily: "var(--mono)",
        }}>
          {index + 1}
        </div>
        <span style={{ flex: 1, fontWeight: 600, fontSize: 14, color: "var(--text-primary)" }}>
          {chapter.title}
        </span>
        <span style={{
          color: "var(--text-muted)", fontSize: 16,
          transform: isOpen ? "rotate(90deg)" : "rotate(0deg)",
          transition: "transform 0.2s",
        }}>›</span>
      </button>

      {isOpen && (
        <div style={{
          padding: "0 18px 18px",
          fontSize: 13.5, lineHeight: 1.7,
          color: "var(--text-secondary)",
          animation: "fadeIn 0.2s ease",
          borderTop: "1px solid var(--white-10)",
          paddingTop: 14,
        }}>
          {renderContent(chapter.content)}
        </div>
      )}
    </div>
  );
}
