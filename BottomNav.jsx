import React, { useState, useRef } from "react";
import { api } from "../utils/api";
import { BackButton, Button, Spinner, Divider } from "../components/UI";

const SUBJECT_NAMES = { f1: "F1 — Business & Technology", f3: "F3 — Financial Accounting", fm: "Financial Markets", macro: "Macroeconomics" };

const STEPS = ["Choose", "Pay", "Upload", "Pending"];

export default function PaymentPage({ navigate, subjectKey }) {
  const [step, setStep] = useState(0); // 0=promo, 1=pay, 2=upload, 3=done
  const [promo, setPromo] = useState("");
  const [promoResult, setPromoResult] = useState(null);
  const [promoLoading, setPromoLoading] = useState(false);
  const [paymentInfo, setPaymentInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [screenshot, setScreenshot] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef();

  const subjectName = SUBJECT_NAMES[subjectKey] || subjectKey;

  const handleCheckPromo = async () => {
    if (!promo.trim()) return;
    setPromoLoading(true);
    try {
      const res = await api.checkPromo(promo.trim().toUpperCase());
      setPromoResult(res);
    } catch { setPromoResult({ valid: false }); }
    setPromoLoading(false);
  };

  const handleRequestPayment = async () => {
    setLoading(true);
    try {
      const res = await api.requestPayment(subjectKey, promoResult?.valid ? promo.trim().toUpperCase() : "");
      if (res.error === "already_owned") {
        alert("You already own this subject!");
        navigate("subject", { subjectKey });
        return;
      }
      setPaymentInfo(res);
      setStep(1);
    } catch (e) {
      alert(e.message || "Error creating payment request");
    }
    setLoading(false);
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setScreenshot(ev.target.result);
    reader.readAsDataURL(file);
  };

  const handleUploadScreenshot = async () => {
    if (!screenshot) return;
    setUploading(true);
    try {
      await api.uploadScreenshot(subjectKey, screenshot);
      setStep(3);
    } catch { alert("Upload failed, please try again."); }
    setUploading(false);
  };

  const copyCard = () => {
    navigator.clipboard.writeText(paymentInfo?.card || "");
    window.Telegram?.WebApp?.showAlert?.("Card number copied!");
  };

  // Step 0 — Promo + Confirm
  if (step === 0) return (
    <div style={{ padding: "20px 16px" }}>
      <BackButton onClick={() => navigate("home")} />
      <div style={{ fontSize: 36, marginBottom: 10 }}>🛒</div>
      <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>Buy Access</h1>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 24 }}>{subjectName}</p>

      {/* Price card */}
      <div style={{
        background: "linear-gradient(135deg, rgba(79,142,247,0.18) 0%, rgba(37,99,235,0.1) 100%)",
        border: "1px solid rgba(79,142,247,0.3)",
        borderRadius: "var(--radius-lg)", padding: "20px",
        marginBottom: 20,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 14, color: "var(--text-secondary)" }}>Price</span>
          <span style={{ fontSize: 22, fontWeight: 800, color: "var(--gold)" }}>
            {promoResult?.valid ? promoResult.price?.toLocaleString() : "50,000"} UZS
          </span>
        </div>
        {promoResult?.valid && (
          <div style={{ fontSize: 12, color: "var(--green)", marginTop: 4 }}>
            🎉 Promo applied! {promoResult.discount}% off
          </div>
        )}
      </div>

      {/* Promo code */}
      <div style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8 }}>🎁 Have a promo code?</p>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={promo}
            onChange={e => setPromo(e.target.value.toUpperCase())}
            placeholder="PROMO CODE"
            style={{
              flex: 1, background: "var(--card-bg)",
              border: `1px solid ${promoResult?.valid ? "var(--green)" : promoResult?.valid === false ? "var(--red)" : "var(--card-border)"}`,
              borderRadius: "var(--radius-sm)", padding: "10px 14px",
              color: "var(--text-primary)", fontFamily: "var(--mono)",
              fontSize: 13, outline: "none",
            }}
          />
          <Button onClick={handleCheckPromo} variant="secondary" small disabled={promoLoading}>
            {promoLoading ? <Spinner size={14} /> : "Apply"}
          </Button>
        </div>
        {promoResult?.valid === false && (
          <p style={{ fontSize: 12, color: "var(--red)", marginTop: 4 }}>Invalid promo code</p>
        )}
      </div>

      <Divider />

      {/* What you get */}
      <div style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>✅ Full access includes:</p>
        {["📖 Full study notes", "🃏 Flashcards", "✏️ 20 MCQ practice tests", "📊 Progress tracking"].map(item => (
          <div key={item} style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 5 }}>{item}</div>
        ))}
      </div>

      <Button onClick={handleRequestPayment} disabled={loading} style={{ width: "100%" }}>
        {loading ? <Spinner size={16} /> : "Proceed to Payment →"}
      </Button>
    </div>
  );

  // Step 1 — Pay
  if (step === 1) return (
    <div style={{ padding: "20px 16px" }}>
      <div style={{ fontSize: 36, marginBottom: 10 }}>💳</div>
      <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>Make Payment</h1>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 24 }}>{subjectName}</p>

      <div style={{
        background: "var(--card-bg)", border: "1px solid var(--card-border)",
        borderRadius: "var(--radius-lg)", padding: 20, marginBottom: 16,
      }}>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 6 }}>Transfer amount</p>
        <p style={{ fontSize: 26, fontWeight: 800, color: "var(--gold)", marginBottom: 16 }}>
          {paymentInfo?.price?.toLocaleString()} UZS
        </p>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 8 }}>Transfer to card:</p>
        <div style={{
          background: "rgba(255,255,255,0.05)", borderRadius: "var(--radius-sm)",
          padding: "12px 14px", display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span style={{ fontFamily: "var(--mono)", fontSize: 15, letterSpacing: "2px", color: "var(--accent-bright)" }}>
            {paymentInfo?.card}
          </span>
          <button onClick={copyCard} style={{
            background: "none", border: "none", cursor: "pointer",
            color: "var(--text-secondary)", fontSize: 18,
          }}>📋</button>
        </div>
      </div>

      <div style={{
        background: "rgba(245,200,66,0.08)", border: "1px solid rgba(245,200,66,0.2)",
        borderRadius: "var(--radius)", padding: "12px 14px", marginBottom: 20,
        fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5,
      }}>
        ⚠️ After sending the payment, upload a screenshot on the next step. Access will be opened within 30 minutes.
      </div>

      <Button onClick={() => setStep(2)} style={{ width: "100%" }}>
        I've Paid → Upload Screenshot
      </Button>
    </div>
  );

  // Step 2 — Upload screenshot
  if (step === 2) return (
    <div style={{ padding: "20px 16px" }}>
      <div style={{ fontSize: 36, marginBottom: 10 }}>📸</div>
      <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>Upload Screenshot</h1>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 24 }}>
        Take a screenshot of your payment confirmation and upload it here.
      </p>

      <div
        onClick={() => fileRef.current?.click()}
        style={{
          border: `2px dashed ${screenshot ? "var(--accent)" : "var(--card-border)"}`,
          borderRadius: "var(--radius-lg)", padding: "36px 20px",
          display: "flex", flexDirection: "column", alignItems: "center", gap: 10,
          cursor: "pointer", marginBottom: 20,
          background: screenshot ? "rgba(79,142,247,0.05)" : "transparent",
          transition: "all 0.2s",
        }}
      >
        {screenshot ? (
          <img src={screenshot} alt="preview" style={{ maxWidth: "100%", maxHeight: 200, borderRadius: "var(--radius)" }} />
        ) : (
          <>
            <div style={{ fontSize: 40 }}>📁</div>
            <p style={{ fontSize: 14, fontWeight: 600 }}>Tap to choose image</p>
            <p style={{ fontSize: 12, color: "var(--text-muted)" }}>JPG, PNG supported</p>
          </>
        )}
      </div>
      <input ref={fileRef} type="file" accept="image/*" onChange={handleFileChange} style={{ display: "none" }} />

      <Button onClick={handleUploadScreenshot} disabled={!screenshot || uploading} style={{ width: "100%", marginBottom: 10 }}>
        {uploading ? <Spinner size={16} /> : "Send Screenshot ✓"}
      </Button>
      <Button onClick={() => setStep(3)} variant="ghost" style={{ width: "100%" }}>
        Skip (send later via bot)
      </Button>
    </div>
  );

  // Step 3 — Pending
  return (
    <div style={{ padding: 24, display: "flex", flexDirection: "column", alignItems: "center", gap: 20, marginTop: 60 }}>
      <div style={{ fontSize: 56 }}>⏳</div>
      <h2 style={{ fontSize: 22, fontWeight: 800, textAlign: "center" }}>Payment Pending</h2>
      <div style={{
        background: "var(--card-bg)", border: "1px solid var(--card-border)",
        borderRadius: "var(--radius-lg)", padding: 20, width: "100%", textAlign: "center",
        lineHeight: 1.6,
      }}>
        <p style={{ fontSize: 14, color: "var(--text-secondary)" }}>
          Your payment is being reviewed by the admin.<br />
          You'll receive a Telegram notification once access is granted.<br />
          <strong style={{ color: "var(--text-primary)" }}>Usually within 30 minutes.</strong>
        </p>
      </div>
      <Button onClick={() => navigate("home")} style={{ width: "100%" }}>← Back to Home</Button>
    </div>
  );
}
