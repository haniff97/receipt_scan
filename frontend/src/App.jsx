import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { translate } from "./i18n";
import { 
  Settings, 
  Bell, 
  Scan, 
  Type, 
  ExternalLink, 
  Globe, 
  Search, 
  Mic, 
  Layers, 
  Sparkles, 
  Camera,
  Plus,
  AlertTriangle,
  ReceiptText,
  Download
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";
const API_ORIGIN = API.replace(/\/api$/, "");

export default function App() {
  const [activeTab, setActiveTab] = useState("home");
  const [lang, setLang] = useState(() => localStorage.getItem("lang") || "en");
  const t = (k, v) => translate(lang, k, v);
  const catName = (c) => t(`cat.${c}`);
  const [currency, setCurrency] = useState(() => localStorage.getItem("currency") || "RM");
  const [aiEnabled, setAiEnabled] = useState(() => localStorage.getItem("aiEnabled") !== "off");
  const [stats, setStats] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [rejectedAnomalies, setRejectedAnomalies] = useState([]);
  const [receipts, setReceipts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [dash, setDash] = useState({ today: 0, week: 0, month: 0, monthly: [], byCategory: [] });
  const [dashSummary, setDashSummary] = useState(null);
  const [dashFilter, setDashFilter] = useState({ category: "", period: "" });
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [showAlerts, setShowAlerts] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [showNotify, setShowNotify] = useState(false);
  const [selectedReceipt, setSelectedReceipt] = useState(null);
  const [selectMode, setSelectMode] = useState(false);
  const [receiptFilter, setReceiptFilter] = useState("all");
  const [selectedForDelete, setSelectedForDelete] = useState([]);
  const [receiptCategory, setReceiptCategory] = useState("groceries");
  const [customCategory, setCustomCategory] = useState("");
  const [receiptPreview, setReceiptPreview] = useState(null);
  const [receiptOriginal, setReceiptOriginal] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [editTotal, setEditTotal] = useState(null);
  const [editTxId, setEditTxId] = useState(null);
  const [msg, setMsg] = useState("");
  const [feedbackText, setFeedbackText] = useState("");
  const searchRef = useRef(null);
  const fileRef = useRef(null);
  const cameraRef = useRef(null);

  const refresh = async () => {
    try {
      const [s, a, r, d, t, sm] = await Promise.allSettled([
        axios.get(`${API}/stats`),
        axios.get(`${API}/anomalies`, { params: { lang } }),
        axios.get(`${API}/receipts`),
        axios.get(`${API}/dashboard`),
        axios.get(`${API}/transactions`),
        axios.get(`${API}/dashboard/summary`, { params: { currency, lang } }),
      ]);
      if (s.status === "fulfilled") setStats(s.value.data);
      if (a.status === "fulfilled") {
        setAnomalies(a.value.data.anomalies);
        setRejectedAnomalies(a.value.data.rejected || []);
      }
      if (r.status === "fulfilled") setReceipts(r.value.data);
      if (d.status === "fulfilled") setDash(d.value.data);
      if (t.status === "fulfilled") setTransactions(t.value.data);
      if (sm.status === "fulfilled") setDashSummary(sm.value.data.summary);
    } catch (e) {
      setMsg(t("not_reachable"));
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (activeTab === "dashboard") refresh();
  }, [activeTab]);

  useEffect(() => {
    if (anomalies.length > 0 && !showAlerts) {
      setShowNotify(true);
      const timer = setTimeout(() => setShowNotify(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [anomalies]);

  const runQuery = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    const r = await axios.get(`${API}/query`, { params: { q: query, lang } });
    setResult(r.data);
  };

  const uploadReceipt = async (file) => {
    if (!file) return;
    const category = receiptCategory === "__other__"
      ? (customCategory.trim() || "other")
      : receiptCategory;
    setMsg("");
    setProcessing(true);
    setReceiptOriginal(URL.createObjectURL(file));
    setReceiptPreview(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("category", category);
      if (!aiEnabled) fd.append("ai", "off");
      const r = await axios.post(`${API}/receipts/upload`, fd);

      const backendImg = `${API_ORIGIN}${r.data.image_url || `/api/receipts/${r.data.id}/image`}`;
      setReceiptPreview(backendImg);
      setEditTotal(r.data.amount ?? null);
      setEditTxId(r.data.transaction_id ?? null);
      setConfirming(true);
      await refresh();
    } catch (err) {
      setMsg(err.response?.data?.detail || t("upload_failed"));
    } finally {
      setProcessing(false);
    }
  };

  const saveEditedTotal = async () => {
    if (editTxId === null) return;
    try {
      const txs = transactions;
      const cur = txs.find((x) => x.id === editTxId);
      await axios.patch(`${API}/transactions/${editTxId}`, {
        date: cur ? cur.date : new Date().toISOString(),
        amount: parseFloat(editTotal),
        merchant: cur ? cur.merchant : "Unknown",
        category: cur ? cur.category : (receiptCategory === "__other__" ? (customCategory.trim() || "other") : receiptCategory),
        description: cur ? cur.description : "",
      });
      setConfirming(false);
      setMsg(t("total_updated"));
      await refresh();
    } catch (err) {
      setMsg(err.response?.data?.detail || t("delete_failed"));
    }
  };

  const toggleSelectReceipt = (id) => {
    setSelectedForDelete((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const deleteSelectedReceipts = async () => {
    if (selectedForDelete.length === 0) return;
    try {
      await Promise.all(
        selectedForDelete.map((id) => axios.delete(`${API}/receipts/${id}`))
      );
      setSelectedForDelete([]);
      setSelectMode(false);
      setMsg(t("deleted"));
      await refresh();
    } catch (err) {
      setMsg(err.response?.data?.detail || t("delete_failed"));
    }
  };

  const resetScan = () => {
    setReceiptPreview(null);
    setReceiptOriginal(null);
    setMsg("");
    setConfirming(false);
    setEditTotal(null);
    setEditTxId(null);
    setProcessing(false);
    setReceiptCategory("groceries");
    setCustomCategory("");
  };

  const $ = (n) => {
    if (n === null || n === undefined) return "-";
    const symbol = currency === "RM" ? "RM " : "$";
    return `${symbol}${Number(n).toFixed(2)}`;
  };

  const dashFiltered = useMemo(() => {
    const now = new Date();
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay());
    startOfWeek.setHours(0, 0, 0, 0);
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

    return transactions.filter((t) => {
      if (dashFilter.category && t.category !== dashFilter.category) return false;
      if (dashFilter.period === "today") {
        const d = new Date(t.date);
        if (d.toDateString() !== now.toDateString()) return false;
      }
      if (dashFilter.period === "week") {
        const d = new Date(t.date);
        if (d < startOfWeek) return false;
      }
      if (dashFilter.period === "month") {
        const d = new Date(t.date);
        if (d < startOfMonth) return false;
      }
      return true;
    });
  }, [transactions, dashFilter]);

  const filteredReceipts = useMemo(() => {
    const now = new Date();
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay());
    startOfWeek.setHours(0, 0, 0, 0);
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

    return receipts.filter((r) => {
      const d = new Date(r.uploaded_at);
      if (receiptFilter === "day" && d.toDateString() !== now.toDateString()) return false;
      if (receiptFilter === "week" && d < startOfWeek) return false;
      if (receiptFilter === "month" && d < startOfMonth) return false;
      return true;
    });
  }, [receipts, receiptFilter]);

  const exportCsv = () => {
    if (transactions.length === 0) return;
    const header = "Date,Merchant,Category,Amount,Description";
    const rows = transactions.map((t) =>
      [
        t.date.slice(0, 10),
        `"${(t.merchant || "").replace(/"/g, '""')}"`,
        `"${(t.category || "").replace(/"/g, '""')}"`,
        t.amount,
        `"${(t.description || "").replace(/"/g, '""')}"`,
      ].join(",")
    );
    const csv = [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `receipts_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{
      maxWidth: 420,
      margin: "0 auto",
      minHeight: "100vh",
      background: "var(--bg)",
      padding: "24px 20px 100px",
      display: "flex",
      flexDirection: "column",
      gap: 24,
      position: "relative"
    }}>
      {/* Notification toast */}
      {showNotify && anomalies[0] && (
        <button
          onClick={() => { setShowNotify(false); setShowAlerts(true); }}
          style={{
            position: "fixed",
            top: 16,
            left: 20,
            right: 20,
            maxWidth: 380,
            margin: "0 auto",
            zIndex: 100,
            background: "#fff4f0",
            border: "1px solid #ffd8cc",
            borderRadius: 16,
            padding: 14,
            textAlign: "left",
            boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
            animation: "slideDown 0.3s ease"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 20 }}>🔔</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 14 }}>{t("unusual_spending")}</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                {t("unusual_spending_body", {
                  merchant: anomalies[0].merchant,
                  amount: $(anomalies[0].amount),
                  x: anomalies[0].vs_median,
                  cat: anomalies[0].category,
                })}
              </div>
            </div>
          </div>
          <div style={{ fontSize: 11, color: "var(--orange)", marginTop: 6, textAlign: "right" }}>{t("tap_see_alerts")}</div>
        </button>
      )}

      {/* Header */}
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "32px" }}>
        <button onClick={() => setActiveTab("settings")} style={{ color: "var(--text-main)", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Settings size={24} strokeWidth={1.5} />
        </button>
        <button onClick={() => setShowAlerts(!showAlerts)} style={{ color: "var(--text-main)", position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Bell size={24} strokeWidth={1.5} />
          {anomalies.length > 0 && (
            <span style={{
              position: "absolute",
              top: -2,
              right: -2,
              background: "var(--orange)",
              color: "#fff",
              fontSize: 10,
              fontWeight: "bold",
              width: 16,
              height: 16,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: "2px solid var(--bg)"
            }}>
              {anomalies.length}
            </span>
          )}
        </button>
      </header>

      {/* Main Home View Elements */}
      {activeTab === "home" && (
        <>
          {/* Alerts panel */}
      {showAlerts && (
        <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.06)" }}>
          <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 8 }}>{t("alerts")}</div>
          <div style={{ color: "var(--text-muted)", fontSize: 12, marginBottom: 10 }}>
            {t("reviewed_by_ai")}
          </div>
          {anomalies.length === 0 && rejectedAnomalies.length === 0 && <div style={{ color: "var(--text-muted)", fontSize: 13 }}>{t("none_detected")}</div>}
          {anomalies.map((a) => (
            <div key={a.id} style={{ background: "#fff4f0", borderRadius: 12, padding: 10, marginBottom: 8, fontSize: 13 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{a.merchant}</strong>
                <strong>{$(a.amount)}</strong>
              </div>
              <div style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 2 }}>{catName(a.category)} · {a.vs_median}x usual</div>
              {a.ai_reason && <div style={{ color: "var(--orange)", fontSize: 12, marginTop: 4 }}>{a.ai_reason}</div>}
            </div>
          ))}
          {rejectedAnomalies.map((a) => (
            <div key={a.id} style={{ background: "var(--bg)", borderRadius: 12, padding: 10, marginBottom: 8, fontSize: 13, opacity: 0.85 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ textDecoration: "line-through" }}>{a.merchant}</span>
                <span>{$(a.amount)}</span>
              </div>
              <div style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 2 }}>AI: not an anomaly</div>
              {a.ai_reason && <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 4 }}>{a.ai_reason}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Greeting */}
      <div style={{ marginBottom: "8px" }}>
        <h1 style={{ 
          fontSize: 32, 
          margin: 0, 
          fontWeight: 600, 
          color: "var(--text-muted)", 
          letterSpacing: "-0.5px"
        }}>
          {t("hello")}
        </h1>
        <h2 style={{ 
          fontSize: 32, 
          margin: "4px 0 0", 
          fontWeight: 700, 
          color: "var(--text-main)", 
          letterSpacing: "-0.5px",
          lineHeight: 1.1
        }}
          dangerouslySetInnerHTML={{ __html: t("ready_to_scan") }}
        />
      </div>

      {/* Stats */}
      {stats && (
        <div style={{ display: "flex", gap: 12 }}>
          <div style={{ flex: 1, background: "var(--card)", borderRadius: 20, padding: 16, textAlign: "center" }}>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{t("total_spent")}</div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>{$(stats.total_spent)}</div>
          </div>
          <div style={{ flex: 1, background: "var(--card)", borderRadius: 20, padding: 16, textAlign: "center" }}>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{t("transactions")}</div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>{stats.transaction_count}</div>
          </div>
        </div>
      )}

      {/* 2x2 Grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 16
      }}>
        <button className="action-card" onClick={() => setActiveTab("scan")} style={{
          background: "var(--card)",
          borderRadius: 24,
          padding: 20,
          textAlign: "left",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          boxShadow: "0 2px 10px rgba(0,0,0,0.02)"
        }}>
          <Scan size={28} color="var(--text-muted)" strokeWidth={1.5} style={{ marginBottom: 20 }} />
          <div style={{ fontWeight: 600, fontSize: 18, marginBottom: 4, color: "var(--text-main)" }}>{t("scan")}</div>
          <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{t("receipt_photo_read")}</div>
        </button>

        <button className="action-card" onClick={() => setActiveTab("receipts")} style={{
          background: "var(--card)",
          borderRadius: 24,
          padding: 20,
          textAlign: "left",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          boxShadow: "0 2px 10px rgba(0,0,0,0.02)"
        }}>
          <ReceiptText size={28} color="var(--text-muted)" strokeWidth={1.5} style={{ marginBottom: 20 }} />
          <div style={{ fontWeight: 600, fontSize: 18, marginBottom: 4, color: "var(--text-main)" }}>{t("receipts")}</div>
          <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{t("saved_tap_to_view", { n: receipts.length })}</div>
        </button>

        <button className="action-card" onClick={() => setActiveTab("dashboard")} style={{
          background: "var(--card)",
          borderRadius: 24,
          padding: 20,
          textAlign: "left",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          boxShadow: "0 2px 10px rgba(0,0,0,0.02)"
        }}>
          <ExternalLink size={28} color="var(--text-muted)" strokeWidth={1.5} style={{ marginBottom: 20 }} />
          <div style={{ fontWeight: 600, fontSize: 18, marginBottom: 4, color: "var(--text-main)" }}>{t("dashboard")}</div>
          <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{t("day_week_month")}</div>
        </button>

        <button className="action-card" onClick={() => setActiveTab("alerts")} style={{
          background: "var(--card)",
          borderRadius: 24,
          padding: 20,
          textAlign: "left",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          boxShadow: "0 2px 10px rgba(0,0,0,0.02)"
        }}>
          <AlertTriangle size={28} color="var(--orange)" strokeWidth={1.5} style={{ marginBottom: 20 }} />
          <div style={{ fontWeight: 600, fontSize: 18, marginBottom: 4, color: "var(--text-main)" }}>{t("alerts")}</div>
          <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{t("above_usual", { n: anomalies.length })}</div>
        </button>
      </div>
        </>
      )}

      {/* AI page — dedicated chat */}
      {activeTab === "ai" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>{t("ask_ai")}</h2>

          <form onSubmit={runQuery} style={{
            background: "var(--bg)",
            border: "1px solid #e0e0e0",
            borderRadius: 30,
            padding: "12px 16px",
            display: "flex",
            alignItems: "center",
            gap: 12
          }}>
            <Search size={20} color="var(--text-muted)" />
            <input
              ref={searchRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("ask_placeholder")}
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                fontSize: 16,
                color: "var(--text-main)"
              }}
            />
            <button type="submit" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Mic size={20} color="var(--text-muted)" />
            </button>
          </form>

          {result && (
            <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.06)" }}>
              <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 6 }}>{result.answer}</div>
              <div style={{ color: "var(--text-muted)", fontSize: 12, marginBottom: 8 }}>
                Filters: {Object.keys(result.filters).length ? JSON.stringify(result.filters) : "none"}
              </div>
              <div style={{ maxHeight: 400, overflowY: "auto", paddingRight: 8 }}>
                {(result.transactions || []).map((t, i) => (
                  <div key={i} style={{ fontSize: 13, padding: "6px 0", borderTop: "1px solid var(--border)" }}>
                    {t.date.slice(0, 10)} · {t.merchant} · <strong>{$(t.amount)}</strong> <span style={{ color: "var(--text-muted)" }}>({catName(t.category)})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Scan page */}
      {activeTab === "scan" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>{t("scan_receipt")}</h2>

          <button
            className="action-card"
            onClick={() => cameraRef.current?.click()}
            style={{
              background: "var(--card)",
              borderRadius: 24,
              padding: 32,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 12,
              boxShadow: "0 2px 10px rgba(0,0,0,0.03)"
            }}
          >
            <div style={{ width: 72, height: 72, borderRadius: "50%", background: "var(--accent-soft)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Camera size={36} color="var(--accent)" strokeWidth={1.5} />
            </div>
            <div style={{ fontWeight: 600, fontSize: 16 }}>{t("tap_capture")}</div>
            <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{t("uses_camera")}</div>
          </button>

          <button
            className="action-card"
            onClick={() => fileRef.current?.click()}
            style={{
              background: "var(--card)",
              borderRadius: 16,
              padding: 14,
              textAlign: "center",
              fontSize: 14,
              color: "var(--text-muted)",
              boxShadow: "0 2px 10px rgba(0,0,0,0.03)"
            }}
          >
            {t("or_gallery")}
          </button>


          <input
            ref={cameraRef}
            type="file"
            accept="image/*,.pdf"
            capture="environment"
            style={{ display: "none" }}
            onChange={(e) => {
              uploadReceipt(e.target.files[0]);
              e.target.value = "";
            }}
          />

          <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 8 }}>{t("receipt_category")}</div>
            <select
              value={receiptCategory}
              onChange={(e) => setReceiptCategory(e.target.value)}
              style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border)", background: "#fff" }}
            >
              {["groceries", "dining", "transport", "shopping", "utilities", "entertainment", "health", "travel"].map((c) => (
                <option key={c} value={c}>{catName(c)}</option>
              ))}
              <option value="__other__">{t("other")}</option>
            </select>
            {receiptCategory === "__other__" && (
              <input
                value={customCategory}
                onChange={(e) => setCustomCategory(e.target.value)}
                placeholder={t("type_new_category")}
                style={{ width: "100%", marginTop: 10, padding: 12, borderRadius: 12, border: "1px solid var(--border)", background: "#fff" }}
              />
            )}
          </div>

          {processing && (
            <div style={{
              background: "var(--card)",
              borderRadius: 20,
              padding: 24,
              textAlign: "center",
              boxShadow: "0 2px 10px rgba(0,0,0,0.03)",
            }}>
              <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 14, color: "var(--text-main)" }}>
                {t("scanning")}
              </div>

              {/* Modern scan viewport */}
              <div className="scan-viewport">
                {/* Pulse rings */}
                <div className="scan-ring" />
                <div className="scan-ring" />

                {/* Corner brackets */}
                <div className="scan-brackets">
                  <div className="br" />
                </div>

                {/* Sweeping beam */}
                <div className="scan-beam" />

                {/* Status dots */}
                <div className="scan-dots">
                  <div className="scan-dot" />
                  <div className="scan-dot" />
                  <div className="scan-dot" />
                </div>

                {/* Label inside dark viewport */}
                <div style={{
                  position: "absolute",
                  top: "50%",
                  left: "50%",
                  translate: "-50% -50%",
                  color: "rgba(162,155,254,0.7)",
                  fontSize: 11,
                  fontWeight: 500,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  marginTop: 36,
                  whiteSpace: "nowrap"
                }}>
                  Reading receipt
                </div>
              </div>

              <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 14 }}>
                {aiEnabled ? "AI is extracting merchant, date & total…" : t("detecting_edges")}
              </div>
            </div>
          )}

          {receiptPreview && !processing && (
            <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
              <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 8 }}>{t("scanned_document")}</div>

              {receiptOriginal && (
                <div className="morph-panel" style={{ background: "#fff", borderRadius: 12, overflow: "hidden", padding: 6, boxShadow: "0 2px 10px rgba(0,0,0,0.08)", position: "relative" }}>
                  <img src={receiptPreview} alt="scanned receipt" style={{ width: "100%", maxHeight: 320, objectFit: "contain", borderRadius: 8 }} />
                </div>
              )}

              {confirming && (
                <div style={{ background: "#f4f4f6", borderRadius: 12, padding: 14, marginTop: 4 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6 }}>{t("confirm_total")}</div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span style={{ fontSize: 16, fontWeight: 700 }}>{currency === "RM" ? "RM" : "$"}</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={editTotal ?? ""}
                      onChange={(e) => setEditTotal(e.target.value)}
                      style={{ flex: 1, padding: 10, borderRadius: 10, border: "1px solid var(--border)", background: "#fff", fontSize: 16, fontWeight: 600 }}
                    />
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 6 }}>
                    {t("check_against_receipt")}
                  </div>
                  <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                    <button onClick={saveEditedTotal} style={{ flex: 1, background: "#111111", borderRadius: 12, padding: 12, color: "#fff", fontWeight: 600 }}>
                      {t("save")}
                    </button>
                    <button onClick={resetScan} className="secondary" style={{ flex: 1, background: "#eceafb", color: "#6c5ce7", borderRadius: 12, padding: 12, fontWeight: 600 }}>
                      {t("rescan")}
                    </button>
                  </div>
                </div>
              )}

              <button onClick={resetScan} style={{ width: "100%", marginTop: 4, background: "#111111", borderRadius: 12, padding: 14, color: "#fff", fontWeight: 600 }}>
                {t("done")}
              </button>
            </div>
          )}

          {msg && <div style={{ color: "var(--orange)", fontSize: 13 }}>{msg}</div>}
        </div>
      )}

      {/* Alerts page */}
      {activeTab === "alerts" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>Alerts & Anomalies</h2>
          {anomalies.length === 0 ? (
            <div style={{ background: "var(--card)", borderRadius: 20, padding: 32, textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>
              {t("no_unusual")}
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {anomalies.map((a) => (
                <div key={a.id} style={{ background: "#fff4f0", borderRadius: 16, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.02)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <strong style={{ fontSize: 15 }}>{a.merchant}</strong>
                    <strong style={{ fontSize: 15 }}>{$(a.amount)}</strong>
                  </div>
                  <div style={{ color: "var(--text-muted)", fontSize: 13, marginBottom: 8 }}>{catName(a.category)}</div>
                  <div style={{ color: "var(--orange)", fontSize: 13, fontWeight: 600 }}>
                    <AlertTriangle size={14} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />
                    {a.deviation_pct}% above your typical ${a.threshold} threshold
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Dashboard page */}
      {activeTab === "dashboard" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>{t("dashboard")}</h2>

          <div style={{ background: "linear-gradient(135deg, #6c5ce7, #a29bfe)", borderRadius: 20, padding: 18, color: "#fff", boxShadow: "0 2px 10px rgba(108,92,231,0.25)" }}>
            <div style={{ fontWeight: 600, fontSize: 14, opacity: 0.9, marginBottom: 6 }}>{t("ai_summary")}</div>
            {dashSummary === null
              ? <div style={{ fontSize: 13, opacity: 0.85 }}>{t("generating_summary")}</div>
              : <div style={{ fontSize: 14, lineHeight: 1.5 }}>{dashSummary}</div>}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
            <MiniStat label={t("today")} value={$(dash.today)} tint="#eceafb" color="#6c5ce7" />
            <MiniStat label={t("this_week")} value={$(dash.week)} tint="#e3f4ef" color="#00b894" />
            <MiniStat label={t("this_month")} value={$(dash.month)} tint="#fff4e3" color="#f2994a" />
          </div>

          <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 10 }}>{t("spending_by_month")}</div>
            {dash.monthly.map((m) => {
              const max = Math.max(...dash.monthly.map((x) => x.total), 1);
              return (
                <div key={m.month} style={{ marginBottom: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                    <span style={{ color: "var(--text-muted)" }}>{m.month}</span>
                    <strong>{$(m.total)}</strong>
                  </div>
                  <div style={{ height: 8, background: "var(--border)", borderRadius: 4, marginTop: 4 }}>
                    <div style={{ height: 8, width: `${(m.total / max) * 100}%`, background: "var(--accent)", borderRadius: 4 }} />
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 10 }}>{t("by_category")}</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {dash.byCategory.map((c) => (
                <span key={c.category} style={{ background: "var(--bg)", borderRadius: 20, padding: "6px 12px", fontSize: 13 }}>
                  {catName(c.category)} · <strong>{$(c.total)}</strong>
                </span>
              ))}
            </div>
          </div>

          <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 10 }}>{t("transactions")}</div>
            <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
              <select
                value={dashFilter.category}
                onChange={(e) => setDashFilter((f) => ({ ...f, category: e.target.value }))}
                style={{ flex: 1, minWidth: 120, padding: 8, borderRadius: 10, border: "1px solid var(--border)", background: "#fff" }}
              >
                <option value="">{t("all_categories")}</option>
                {dash.byCategory.map((c) => (
                  <option key={c.category} value={c.category}>{catName(c.category)}</option>
                ))}
              </select>
              <select
                value={dashFilter.period}
                onChange={(e) => setDashFilter((f) => ({ ...f, period: e.target.value }))}
                style={{ flex: 1, minWidth: 120, padding: 8, borderRadius: 10, border: "1px solid var(--border)", background: "#fff" }}
              >
                <option value="">{t("all_time")}</option>
                <option value="today">{t("today")}</option>
                <option value="week">{t("this_week")}</option>
                <option value="month">{t("this_month")}</option>
              </select>
            </div>
            <div style={{ maxHeight: 300, overflowY: "auto" }}>
              {dashFiltered.length === 0 && <div style={{ color: "var(--text-muted)", fontSize: 13 }}>{t("no_transactions_match")}</div>}
              {dashFiltered.map((t) => (
                <div key={t.id} style={{ fontSize: 13, padding: "6px 0", borderTop: "1px solid var(--border)" }}>
                {t.date.slice(0, 10)} · {t.merchant} · <strong>{$(t.amount)}</strong> <span style={{ color: "var(--text-muted)" }}>({catName(t.category)})</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Settings page */}
      {activeTab === "settings" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>{t("settings")}</h2>

          <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 10 }}>Language / Bahasa</div>
            <select
              value={lang}
              onChange={(e) => {
                setLang(e.target.value);
                localStorage.setItem("lang", e.target.value);
              }}
              style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border)", background: "#fff", fontWeight: 600 }}
            >
              <option value="en">English</option>
              <option value="ms">Bahasa Melayu</option>
            </select>
          </div>

          <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 10 }}>{t("currency")}</div>
            <select
              value={currency}
              onChange={(e) => {
                setCurrency(e.target.value);
                localStorage.setItem("currency", e.target.value);
              }}
              style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border)", background: "#fff", fontWeight: 600 }}
            >
              <option value="$">Dollar ($)</option>
              <option value="RM">Ringgit (RM)</option>
            </select>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 10 }}>
              {t("affects_amounts")}
            </div>
          </div>

          <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 8 }}>{t("feedback")}</div>
            <textarea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder={t("feedback_placeholder")}
              rows={4}
              style={{ width: "100%", padding: 12, borderRadius: 12, border: "1px solid var(--border)", background: "#fff", resize: "vertical", fontFamily: "inherit", boxSizing: "border-box" }}
            />
            <button
              onClick={() => setFeedbackText("")}
              style={{
                width: "100%",
                marginTop: 10,
                background: "#111111",
                color: "#fff",
                borderRadius: 12,
                padding: 12,
                fontWeight: 600
              }}
            >
              {t("send_feedback")}
            </button>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
              {t("feedback_note")}
            </div>
          </div>

          <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>{t("ai_assistance")}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                  {t("ai_desc")}
                </div>
              </div>
              <button
                onClick={() => {
                  const next = !aiEnabled;
                  setAiEnabled(next);
                  localStorage.setItem("aiEnabled", next ? "on" : "off");
                }}
                style={{
                  width: 52,
                  height: 30,
                  borderRadius: 15,
                  background: aiEnabled ? "#6c5ce7" : "#ccc",
                  position: "relative",
                  transition: "background 0.2s",
                  flexShrink: 0
                }}
              >
                <span style={{
                  position: "absolute",
                  top: 3,
                  left: aiEnabled ? 25 : 3,
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  background: "#fff",
                  transition: "left 0.2s",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.2)"
                }} />
              </button>
            </div>
            {!aiEnabled && (
              <div style={{ fontSize: 12, color: "var(--orange)", marginTop: 10 }}>
                {t("ai_off_note")}
              </div>
            )}
          </div>

          <div style={{ background: "var(--card)", borderRadius: 20, padding: 16, boxShadow: "0 2px 10px rgba(0,0,0,0.03)" }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 6 }}>{t("about")}</div>
            <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
              {t("app.name")} — {t("app.tagline")}
            </div>
          </div>
        </div>
      )}

      {/* Receipts page */}
      {activeTab === "receipts" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>{t("receipts")}</h2>
            {receipts.length > 0 && (
              <button
                onClick={() => setSelectMode(!selectMode)}
                style={{
                  background: selectMode ? "#111111" : "#eceafb",
                  color: selectMode ? "#fff" : "#6c5ce7",
                  borderRadius: 12,
                  padding: "8px 14px",
                  fontWeight: 600,
                  fontSize: 13
                }}
              >
                {selectMode ? t("cancel") : t("select")}
              </button>
            )}
          </div>

          {receipts.length > 0 && (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <div style={{ display: "flex", gap: 6, flex: 1 }}>
                {[
                  ["all", t("all_time")],
                  ["day", t("today")],
                  ["week", t("this_week")],
                  ["month", t("this_month")],
                ].map(([val, label]) => (
                  <button
                    key={val}
                    onClick={() => setReceiptFilter(val)}
                    style={{
                      flex: 1,
                      background: receiptFilter === val ? "#111111" : "#eceafb",
                      color: receiptFilter === val ? "#fff" : "#6c5ce7",
                      borderRadius: 10,
                      padding: "8px 0",
                      fontWeight: 600,
                      fontSize: 12
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <button
                onClick={exportCsv}
                title="Export CSV"
                style={{
                  background: "#e3f4ef",
                  color: "#00b894",
                  borderRadius: 10,
                  padding: "8px 12px",
                  fontWeight: 600,
                  fontSize: 12
                }}
              >
                <Download size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />
                CSV
              </button>
            </div>
          )}

          {selectMode && (
            <div style={{ background: "#fff4f0", border: "1px solid #ffd8cc", borderRadius: 12, padding: 12 }}>
              <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>
                {selectedForDelete.length === 0
                  ? t("tap_to_select")
                  : t("selected_count", { n: selectedForDelete.length })}
              </div>
              <button
                onClick={deleteSelectedReceipts}
                disabled={selectedForDelete.length === 0}
                style={{
                  width: "100%",
                  background: "#ff6b6b",
                  color: "#fff",
                  borderRadius: 12,
                  padding: 12,
                  fontWeight: 600,
                  opacity: selectedForDelete.length === 0 ? 0.5 : 1
                }}
              >
                {t("delete_selected")}
              </button>
            </div>
          )}

          {receipts.length === 0 && (
            <div style={{ background: "var(--card)", borderRadius: 20, padding: 32, textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>
              {t("no_receipts_yet")}
            </div>
          )}

          {receipts.length > 0 && filteredReceipts.length === 0 && (
            <div style={{ background: "var(--card)", borderRadius: 20, padding: 24, textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>
              {t("no_transactions_match")}
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {filteredReceipts.map((r) => {
              const isSel = selectedForDelete.includes(r.id);
              return (
                <button
                  key={r.id}
                  className="action-card"
                  onClick={() => selectMode
                    ? toggleSelectReceipt(r.id)
                    : setSelectedReceipt(r)}
                  style={{
                    background: "var(--card)",
                    borderRadius: 16,
                    overflow: "hidden",
                    padding: 0,
                    textAlign: "left",
                    boxShadow: "0 2px 10px rgba(0,0,0,0.03)",
                    border: isSel ? "3px solid #ff6b6b" : "3px solid transparent"
                  }}
                >
                  {isSel && (
                    <div style={{
                      position: "absolute",
                      top: 8,
                      right: 8,
                      background: "#ff6b6b",
                      color: "#fff",
                      borderRadius: "50%",
                      width: 24,
                      height: 24,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: 700,
                      fontSize: 12,
                      zIndex: 2
                    }}>
                      ✓
                    </div>
                  )}
                  <img
                    src={`${API_ORIGIN}${r.image_url}`}
                    alt={r.filename}
                    style={{ width: "100%", height: 140, objectFit: "cover", display: "block" }}
                  />
                  <div style={{ padding: 10 }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{r.filename}</div>
                    <div style={{ color: "var(--text-muted)", fontSize: 11 }}>{new Date(r.uploaded_at).toLocaleDateString()}</div>
                  </div>
                </button>
              );
            })}
          </div>

          {selectedReceipt && (
            <div
              onClick={() => setSelectedReceipt(null)}
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0,0,0,0.7)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 100,
                padding: 20
              }}
            >
              <div
                onClick={(e) => e.stopPropagation()}
                style={{
                  background: "var(--card)",
                  borderRadius: 20,
                  maxWidth: 360,
                  width: "100%",
                  padding: 16,
                  position: "relative",
                  maxHeight: "85vh",
                  display: "flex",
                  flexDirection: "column",
                  boxShadow: "0 10px 25px rgba(0,0,0,0.1)"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div style={{ fontWeight: 600, fontSize: 16, color: "var(--text-main)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, paddingRight: 12 }}>
                    {selectedReceipt.filename}
                  </div>
                  <button 
                    onClick={() => setSelectedReceipt(null)}
                    style={{
                      padding: "6px 16px",
                      background: "var(--bg)",
                      color: "var(--text-main)",
                      border: "1px solid var(--border)",
                      borderRadius: 16,
                      fontSize: 14,
                      fontWeight: 600,
                      cursor: "pointer"
                    }}
                  >
                    {t("close")}
                  </button>
                </div>
                
                <div style={{ overflowY: "auto", flex: 1, borderRadius: 12 }}>
                  <img
                    src={`${API_ORIGIN}${selectedReceipt.image_url}`}
                    alt={selectedReceipt.filename}
                    style={{ width: "100%", borderRadius: 12, display: "block" }}
                  />
                  <pre style={{ fontSize: 11, whiteSpace: "pre-wrap", color: "var(--text-muted)", marginTop: 12, padding: 12, background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 8, fontFamily: "inherit" }}>
                    {selectedReceipt.ocr_text || "No raw text available."}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {msg && <div style={{ color: "var(--orange)", fontSize: 13 }}>{msg}</div>}

      {/* Hidden file input for receipt upload */}
      <input
        ref={fileRef}
        type="file"
        accept="image/*,.pdf"
        style={{ display: "none" }}
        onChange={(e) => {
          uploadReceipt(e.target.files[0]);
          e.target.value = "";
        }}
      />

      {/* Floating Bottom Navigation */}
      <div style={{
        position: "fixed",
        bottom: 32,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "flex-start",
        padding: "0 20px",
        maxWidth: 420,
        margin: "0 auto",
        zIndex: 10
      }}>
        <div style={{
          background: "#111111",
          borderRadius: 40,
          display: "flex",
          alignItems: "center",
          padding: "6px",
          gap: "4px"
        }}>
          <button onClick={() => { setActiveTab("home"); setResult(null); setQuery(""); }} style={{
            background: activeTab === "home" ? "#ffffff" : "transparent",
            borderRadius: "50%",
            width: 44,
            height: 44,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: activeTab === "home" ? "#000000" : "#666666"
          }}>
            <Layers size={20} strokeWidth={2} />
          </button>
          <button onClick={() => setActiveTab("scan")} style={{
            background: activeTab === "scan" ? "#ffffff" : "transparent",
            borderRadius: "50%",
            width: 44,
            height: 44,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: activeTab === "scan" ? "#000000" : "#666666"
          }}>
            <Plus size={20} strokeWidth={2} />
          </button>
          <button onClick={() => setActiveTab("ai")} style={{
            background: activeTab === "ai" ? "#ffffff" : "transparent",
            borderRadius: "50%",
            width: 44,
            height: 44,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: activeTab === "ai" ? "#000000" : "#666666"
          }}>
            <Sparkles size={20} strokeWidth={2} />
          </button>
        </div>
      </div>
    </div>
  );
}

function MiniStat({ label, value, tint, color }) {
  return (
    <div style={{ background: tint, borderRadius: 14, padding: 12, textAlign: "center" }}>
      <div style={{ fontSize: 11, color }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700 }}>{value}</div>
    </div>
  );
}
