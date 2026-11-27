import React, { useEffect, useMemo, useRef, useState } from "react";
import { api, getStoredToken, setStoredToken } from "./api";
import {
  ArrowLeftIcon,
  CheckBadgeIcon,
  ChevronDownIcon,
  CopyIcon,
  DownloadIcon,
  EyeIcon,
  EyeOffIcon,
  GisMarketLogo,
  HomeIcon,
  InfoIcon,
  LockIcon,
  LogoutIcon,
  PlusIcon,
  SaveIcon,
  ScaleIcon,
  SearchIcon,
  SendIcon,
  SettingsIcon,
  ShieldAlertIcon,
  SparklesIcon,
  TrashIcon,
  UnlockIcon,
  WalletIcon,
} from "./components/Icons";

const RAG_TEMPLATES = [
  "Jakie są maksymalne kary umowne oraz limity odpowiedzialności wykonawcy?",
  "Czy w opisie przedmiotu zamówienia występują wymagania wskazujące na konkretnego producenta (vendor lock-in)?",
  "Jakie są warunki udziału w postępowaniu dotyczące doświadczenia zespołu i personelu kluczowego?",
  "Jakie są kryteria oceny ofert i ich wagi procentowe?",
  "Jaki jest wymagany termin realizacji zamówienia oraz harmonogram kamieni milowych?",
  "Jakie wymagania stawia zamawiający w zakresie migracji danych, integracji API oraz standardów OGC/INSPIRE?",
  "Jakie jest wymagane wadium oraz zabezpieczenie należytego wykonania umowy?",
  "Jakie są wymagania dotyczące SLA, gwarancji oraz wsparcia powdrożeniowego?",
  "Jakie dokumenty podmiotowe i przedmiotowe należy złożyć wraz z ofertą?",
];

const FORMAT_OPTIONS = [
  "Standard (SWZ)",
  "Zwięzły (Punkty)",
  "Audyt PZP / KIO",
];

function formatPln(val) {
  if (val === null || val === undefined || Number.isNaN(Number(val)))
    return "Brak danych";
  return new Intl.NumberFormat("pl-PL", {
    style: "currency",
    currency: "PLN",
    maximumFractionDigits: 0,
  }).format(Number(val));
}

function renderInlineBold(text) {
  const parts = String(text).split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>;
    }
    return <React.Fragment key={idx}>{part}</React.Fragment>;
  });
}

function MarkdownText({ text }) {
  if (!text) return null;
  const lines = String(text)
    .replace(/^#{1,4}\s+/gm, "")
    .split("\n");
  const blocks = [];
  let listItems = [];

  const flushList = (keyPrefix) => {
    if (listItems.length > 0) {
      blocks.push(
        <ul key={`${keyPrefix}-ul`}>
          {listItems.map((item, i) => (
            <li key={i}>{renderInlineBold(item)}</li>
          ))}
        </ul>,
      );
      listItems = [];
    }
  };

  lines.forEach((rawLine, idx) => {
    const line = rawLine.trim();
    if (!line) {
      flushList(`b-${idx}`);
      return;
    }
    if (/^[-•*]\s+/.test(line)) {
      listItems.push(line.replace(/^[-•*]\s+/, ""));
    } else {
      flushList(`b-${idx}`);
      blocks.push(<p key={`p-${idx}`}>{renderInlineBold(line)}</p>);
    }
  });
  flushList("end");

  return <div className="prose-block">{blocks}</div>;
}

function LoginView({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api.login(username.trim(), password);
      setStoredToken(data.token);
      onLogin(data.user);
    } catch (err) {
      setError(err.message || "Nieprawidłowy login lub hasło.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-brand">
          <GisMarketLogo size={40} />
          <div>
            <div className="brand-title">GisMarket</div>
            <div className="brand-sub">Intelligence AI · Analiza SWZ</div>
          </div>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <div className="form-field">
          <label className="form-label" htmlFor="login-user">
            Login
          </label>
          <input
            id="login-user"
            className="input"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="login-pass">
            Hasło
          </label>
          <div className="password-wrap">
            <input
              id="login-pass"
              className="input"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button
              type="button"
              className="password-eye"
              onClick={() => setShowPassword((s) => !s)}
              aria-label={showPassword ? "Ukryj hasło" : "Pokaż hasło"}
            >
              {showPassword ? <EyeOffIcon /> : <EyeIcon />}
            </button>
          </div>
        </div>

        <button
          className="btn btn-primary"
          style={{ width: "100%", marginTop: 8 }}
          disabled={loading}
          type="submit"
        >
          {loading ? <span className="spinner" /> : "Zaloguj się"}
        </button>
      </form>
    </div>
  );
}

function Sidebar({ user, route, onNavigate, onLogout }) {
  const initial = (user.username || "U").slice(0, 2).toUpperCase();
  return (
    <aside className="sidebar">
      <button
        type="button"
        className="sidebar-logo"
        onClick={() => onNavigate("home")}
      >
        <GisMarketLogo size={36} />
        <div>
          <div className="brand-title" style={{ fontSize: 15 }}>
            GisMarket
          </div>
          <div className="brand-sub">Intelligence AI</div>
        </div>
      </button>

      <div className="user-card">
        <div className="user-avatar">{initial}</div>
        <div className="user-card-meta">
          <div className="user-card-name">{user.username}</div>
          <div className="user-card-role">
            {user.role === "admin" ? "Administrator" : "Użytkownik"}
          </div>
        </div>
      </div>

      <nav className="nav-list" aria-label="Nawigacja główna">
        <button
          type="button"
          className={`nav-item ${route === "home" || route === "detail" ? "active" : ""}`}
          onClick={() => onNavigate("home")}
        >
          <HomeIcon size={18} />
          <span>Główna</span>
        </button>
        <button
          type="button"
          className={`nav-item ${route === "settings" ? "active" : ""}`}
          onClick={() => onNavigate("settings")}
        >
          <SettingsIcon size={18} />
          <span>Ustawienia</span>
        </button>
        <button
          type="button"
          className={`nav-item ${route === "about" ? "active" : ""}`}
          onClick={() => onNavigate("about")}
        >
          <InfoIcon size={18} />
          <span>O programie</span>
        </button>

        <button type="button" className="nav-item logout" onClick={onLogout}>
          <LogoutIcon size={18} />
          <span>Wyloguj się</span>
        </button>
      </nav>
    </aside>
  );
}

function HomeView({ procurements, loading, error, onOpenTender }) {
  const [search, setSearch] = useState("");
  const [voivodeship, setVoivodeship] = useState("Wszystkie");
  const [minBudget, setMinBudget] = useState("0");

  const voivodeships = useMemo(() => {
    const set = new Set(
      procurements.map((p) => (p.voivodeship || "").trim()).filter(Boolean),
    );
    return [
      "Wszystkie",
      ...Array.from(set).sort((a, b) => a.localeCompare(b, "pl")),
    ];
  }, [procurements]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const minVal = Number(minBudget) || 0;
    return procurements.filter((p) => {
      if (voivodeship !== "Wszystkie" && (p.voivodeship || "") !== voivodeship)
        return false;
      if (minVal > 0 && Number(p.budget_pln || 0) < minVal) return false;
      if (q) {
        const hay =
          `${p.title || ""} ${p.municipality || ""} ${p.id || ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [procurements, search, voivodeship, minBudget]);

  const hasFilters =
    Boolean(search.trim()) || voivodeship !== "Wszystkie" || minBudget !== "0";

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Pulpit przetargów GIS</h1>
          <p className="page-subtitle">
            Kliknij wybrane postępowanie, aby przejść do esencji audytu SWZ i
            czatu z dokumentacją.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {hasFilters && (
            <button
              type="button"
              className="btn btn-secondary btn-compact"
              onClick={() => {
                setSearch("");
                setVoivodeship("Wszystkie");
                setMinBudget("0");
              }}
            >
              Wyczyść filtry
            </button>
          )}
          <span className="badge badge-blue tabular">
            {filtered.length} z {procurements.length}
          </span>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="filters-bar">
        <div className="filter-group">
          <label htmlFor="filter-search">Szukaj</label>
          <div className="input-with-icon">
            <span className="input-leading-icon">
              <SearchIcon size={16} />
            </span>
            <input
              id="filter-search"
              className="input"
              type="text"
              placeholder="Wpisz frazę..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {search && (
              <button
                type="button"
                className="input-clear-btn"
                onClick={() => setSearch("")}
                aria-label="Wyczyść wyszukiwanie"
              >
                ×
              </button>
            )}
          </div>
        </div>

        <div className="filter-group">
          <label htmlFor="filter-voiv">Województwo</label>
          <select
            id="filter-voiv"
            className="input"
            value={voivodeship}
            onChange={(e) => setVoivodeship(e.target.value)}
          >
            {voivodeships.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="filter-budget">Minimalny budżet</label>
          <select
            id="filter-budget"
            className="input"
            value={minBudget}
            onChange={(e) => setMinBudget(e.target.value)}
          >
            <option value="0">Wszystkie</option>
            <option value="100000">≥ 100 000 zł</option>
            <option value="500000">≥ 500 000 zł</option>
            <option value="1000000">≥ 1 000 000 zł</option>
            <option value="3000000">≥ 3 000 000 zł</option>
          </select>
        </div>
      </div>

      <div className="card">
        {loading ? (
          <div
            style={{
              padding: 20,
              display: "flex",
              flexDirection: "column",
              gap: 12,
            }}
          >
            {[1, 2, 3, 4].map((row) => (
              <div
                key={row}
                className="skeleton"
                style={{ height: 42, width: "100%" }}
              />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div
            style={{
              padding: 36,
              textAlign: "center",
              color: "var(--ink-muted)",
            }}
          >
            Brak postępowań spełniających wybrane kryteria.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Przedmiot zamówienia</th>
                  <th>Zamawiający</th>
                  <th>Województwo</th>
                  <th className="num">Budżet netto</th>
                  <th>Termin</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr
                    key={item.id}
                    className="clickable-row"
                    tabIndex={0}
                    onClick={() => onOpenTender(item)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onOpenTender(item);
                      }
                    }}
                  >
                    <td className="tender-title-cell">{item.title}</td>
                    <td>{item.municipality || "—"}</td>
                    <td>{item.voivodeship || "—"}</td>
                    <td
                      className="num tabular"
                      style={{ whiteSpace: "nowrap", fontWeight: 600 }}
                    >
                      {formatPln(item.budget_pln)}
                    </td>
                    <td className="tabular" style={{ whiteSpace: "nowrap" }}>
                      {item.deadline || "—"}
                    </td>
                    <td>
                      <span className="badge badge-gray">
                        {item.status || "Aktywny"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function TenderDetailView({
  tender,
  cachedSummary,
  onCacheSummary,
  messages,
  onUpdateMessages,
  onBack,
}) {
  const [summaryData, setSummaryData] = useState(cachedSummary || null);
  const [loadingSummary, setLoadingSummary] = useState(!cachedSummary);
  const [progress, setProgress] = useState(cachedSummary ? 100 : 18);
  const [summaryError, setSummaryError] = useState("");
  const [auditOpen, setAuditOpen] = useState(false);
  const [auditTab, setAuditTab] = useState("summary");

  const [question, setQuestion] = useState("");
  const [questionQueue, setQuestionQueue] = useState([]);
  const [responseFormat, setResponseFormat] = useState(FORMAT_OPTIONS[0]);
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState("");
  const [templatesOpen, setTemplatesOpen] = useState(false);
  const [openSources, setOpenSources] = useState({});
  const [copiedIdx, setCopiedIdx] = useState(null);

  const chatEndRef = useRef(null);
  const composerRef = useRef(null);
  const abortRef = useRef(null);
  const queuePausedRef = useRef(false);

  const setMessages = (updater) => {
    onUpdateMessages(tender.id, updater);
  };

  useEffect(() => {
    setAuditTab("summary");
    if (cachedSummary) {
      setSummaryData(cachedSummary);
      setLoadingSummary(false);
      setProgress(100);
      return;
    }

    let active = true;
    setLoadingSummary(true);
    setSummaryError("");
    setSummaryData(null);
    setProgress(20);

    const timer = setInterval(() => {
      setProgress((prev) => (prev < 88 ? prev + 12 : prev));
    }, 260);

    api
      .getSummary(tender.id)
      .then((res) => {
        if (!active) return;
        setProgress(100);
        setSummaryData(res);
        onCacheSummary(tender.id, res);
      })
      .catch((err) => {
        if (!active) return;
        setSummaryError(
          err.message || "Nie udało się pobrać analizy przetargu.",
        );
      })
      .finally(() => {
        clearInterval(timer);
        if (active) setLoadingSummary(false);
      });

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [tender.id, cachedSummary]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  useEffect(() => {
    const onDocClick = (e) => {
      if (
        templatesOpen &&
        composerRef.current &&
        !composerRef.current.contains(e.target)
      ) {
        setTemplatesOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [templatesOpen]);

  function handleStopGeneration() {
    queuePausedRef.current = true;
    abortRef.current?.abort();
  }

  function handleRemoveQueued(id) {
    setQuestionQueue((prev) => prev.filter((item) => item.id !== id));
  }

  async function submitQuestion(textToSend, formatOverride) {
    const q = (textToSend ?? question).trim();
    if (!q) return;

    const fmt = formatOverride ?? responseFormat;
    if (asking) {
      setTemplatesOpen(false);
      setQuestion("");
      setQuestionQueue((prev) => [
        ...prev,
        { id: `${Date.now()}-${Math.random()}`, text: q, format: fmt },
      ]);
      return;
    }

    queuePausedRef.current = false;
    setAskError("");
    setTemplatesOpen(false);
    if (textToSend === undefined) {
      setQuestion("");
    }

    const historyPayload = messages
      .filter((m) => m.text)
      .slice(-4)
      .map((m) => ({ role: m.role, content: m.text }));

    setMessages((prev) => [
      ...prev,
      { role: "user", text: q },
      { role: "assistant", text: "", chunks: [] },
    ]);
    setAsking(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await api.askQuestionStream(tender.id, q, fmt, {
        signal: controller.signal,
        history: historyPayload,
        onChunks: (chunks) => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              next[next.length - 1] = { ...last, chunks };
            }
            return next;
          });
        },
        onToken: (token) => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              next[next.length - 1] = { ...last, text: last.text + token };
            }
            return next;
          });
        },
      });
    } catch (err) {
      if (err?.name === "AbortError") {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant") {
            if (!last.text) return prev.slice(0, -1);
            const next = [...prev];
            next[next.length - 1] = {
              ...last,
              text: `${last.text}\n\n*(Generowanie zatrzymane przez użytkownika)*`,
            };
            return next;
          }
          return prev;
        });
      } else {
        setAskError(err.message || "Błąd podczas generowania odpowiedzi.");
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && !last.text) {
            return prev.slice(0, -1);
          }
          return prev;
        });
      }
    } finally {
      abortRef.current = null;
      setAsking(false);
    }
  }

  useEffect(() => {
    if (!asking && !queuePausedRef.current && questionQueue.length > 0) {
      const [nextItem, ...rest] = questionQueue;
      setQuestionQueue(rest);
      submitQuestion(nextItem.text, nextItem.format);
    }
  }, [asking, questionQueue]);

  function handleSend(e) {
    if (e) e.preventDefault();
    submitQuestion();
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitQuestion();
    }
  }

  function handleCopy(text, idx) {
    navigator.clipboard?.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1500);
  }

  const metrics = summaryData?.metrics;
  const sections = summaryData?.sections;
  const faithfulness = summaryData?.faithfulness;
  const kioBadgeClass =
    metrics?.kio_level === "HIGH"
      ? "badge-red"
      : metrics?.kio_level === "MEDIUM"
        ? "badge-amber"
        : "badge-green";

  const auditTabs = [
    {
      id: "summary",
      label: "Podsumowanie",
      visible: Boolean(sections?.summary),
    },
    {
      id: "barriers",
      label: "Bariery PZP / KIO",
      visible: Boolean(sections?.legal_barriers),
    },
    {
      id: "competitors",
      label: "Konkurencja",
      visible: Boolean(metrics?.competitors?.length || sections?.competitors),
    },
    {
      id: "recommendations",
      label: "Rekomendacje",
      visible: Boolean(sections?.recommendations),
    },
  ].filter((t) => t.visible);

  return (
    <div className="detail-shell">
      <div className="detail-scroll">
        <div className="detail-topbar">
          <div className="detail-title-group">
            <button
              type="button"
              className="btn-icon"
              onClick={onBack}
              title="Powrót do listy"
              aria-label="Powrót do listy"
            >
              <ArrowLeftIcon size={18} />
            </button>
            <div>
              <h1 className="detail-title">{tender.title}</h1>
              <div className="detail-meta-row">
                <span>{tender.municipality || "—"}</span>
                <span>·</span>
                <span>{tender.voivodeship || "—"}</span>
                <span>·</span>
                <span className="tabular">
                  Termin: {tender.deadline || "—"}
                </span>
              </div>
            </div>
          </div>

          <a
            className="btn btn-secondary btn-compact"
            href={api.getPdfDownloadUrl(tender.id)}
            target="_blank"
            rel="noreferrer"
            style={{ textDecoration: "none", whiteSpace: "nowrap" }}
          >
            <DownloadIcon size={16} />
            <span>Eksportuj PDF</span>
          </a>
        </div>

        {loadingSummary && (
          <>
            <div className="progress-card">
              <div className="progress-label">
                <span>
                  Przygotowanie esencji SWZ, profilu ryzyka KIO i macierzy
                  konkurencji...
                </span>
                <span className="tabular">{progress}%</span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            <div className="essence-card">
              <div className="kpi-strip">
                {[1, 2, 3, 4].map((n) => (
                  <div key={n} className="kpi-tile">
                    <div
                      className="skeleton"
                      style={{ height: 14, width: "55%", marginBottom: 12 }}
                    />
                    <div
                      className="skeleton"
                      style={{ height: 24, width: "75%", marginBottom: 8 }}
                    />
                    <div
                      className="skeleton"
                      style={{ height: 12, width: "90%" }}
                    />
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {summaryError && (
          <div className="alert alert-error">{summaryError}</div>
        )}

        {metrics && (
          <>
            <div className="essence-card">
              <div className="kpi-strip">
                <div className="kpi-tile">
                  <div className="kpi-head">
                    <span>Ryzyko KIO</span>
                    <ShieldAlertIcon size={16} />
                  </div>
                  <div className="kpi-value">
                    <span className={`badge ${kioBadgeClass}`}>
                      <span className="status-dot" />
                      {metrics.kio_label}
                    </span>
                  </div>
                  <div className="kpi-sub">{metrics.kio_sub}</div>
                </div>

                <div className="kpi-tile">
                  <div className="kpi-head">
                    <span>Wartość netto</span>
                    <WalletIcon size={16} />
                  </div>
                  <div className="kpi-value tabular">
                    {formatPln(tender.budget_pln)}
                  </div>
                  <div className="kpi-sub tabular">
                    Wadium: {metrics.wadium_str || "Brak danych"}
                  </div>
                </div>

                <div className="kpi-tile">
                  <div className="kpi-head">
                    <span>Kary umowne</span>
                    <ScaleIcon size={16} />
                  </div>
                  <div className="kpi-value tabular">
                    {metrics.penalty_rate || "Wg umowy"}
                  </div>
                  <div className="kpi-sub">
                    {metrics.penalty_sub || "Analiza zapisów umowy"}
                  </div>
                </div>

                <div className="kpi-tile">
                  <div className="kpi-head">
                    <span>Wierność RAGAS</span>
                    <CheckBadgeIcon size={16} />
                  </div>
                  <div className="kpi-value tabular">
                    {faithfulness !== null && faithfulness !== undefined
                      ? `${Math.round(Number(faithfulness) * 100)}%`
                      : "—"}
                  </div>
                  <div className="kpi-sub">Weryfikacja BGE-Reranker</div>
                </div>
              </div>
            </div>

            <div className="card audit-panel">
              <button
                type="button"
                className="audit-toggle"
                onClick={() => setAuditOpen((o) => !o)}
                aria-expanded={auditOpen}
              >
                <span>Esencja audytu SWZ i macierz konkurencji</span>
                <ChevronDownIcon size={16} rotated={auditOpen} />
              </button>

              {auditOpen && (
                <div className="audit-body">
                  {metrics.system_tags?.length > 0 && (
                    <div className="tag-row">
                      {metrics.system_tags.map((tag) => (
                        <span key={tag} className="badge badge-blue">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}

                  {auditTabs.length > 0 && (
                    <div className="tabs-bar" role="tablist">
                      {auditTabs.map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          role="tab"
                          aria-selected={auditTab === t.id}
                          className={`tab-btn ${auditTab === t.id ? "active" : ""}`}
                          onClick={() => setAuditTab(t.id)}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>
                  )}

                  {auditTab === "summary" && sections?.summary && (
                    <MarkdownText text={sections.summary} />
                  )}

                  {auditTab === "barriers" && sections?.legal_barriers && (
                    <MarkdownText text={sections.legal_barriers} />
                  )}

                  {auditTab === "competitors" &&
                    (metrics.competitors?.length > 0 ? (
                      <div className="table-wrap">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Podmiot</th>
                              <th>Rozwiązanie / Produkt</th>
                              <th>Przewaga w SWZ</th>
                            </tr>
                          </thead>
                          <tbody>
                            {metrics.competitors.map((comp, idx) => (
                              <tr key={idx}>
                                <td style={{ fontWeight: 600 }}>{comp.name}</td>
                                <td>{comp.product}</td>
                                <td>{comp.advantage}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      sections?.competitors && (
                        <MarkdownText text={sections.competitors} />
                      )
                    ))}

                  {auditTab === "recommendations" &&
                    sections?.recommendations && (
                      <MarkdownText text={sections.recommendations} />
                    )}
                </div>
              )}
            </div>
          </>
        )}

        <div className="card chat-card">
          <div className="chat-header">
            <h3>Rozmowa z dokumentacją SWZ</h3>
            {messages.length > 0 && (
              <button
                type="button"
                className="btn btn-secondary btn-compact"
                onClick={() => {
                  queuePausedRef.current = true;
                  abortRef.current?.abort();
                  setQuestionQueue([]);
                  setMessages([]);
                }}
              >
                Wyczyść
              </button>
            )}
          </div>

          {askError && <div className="alert alert-error">{askError}</div>}

          {messages.length === 0 && !asking ? (
            <div className="chat-empty">
              Zadaj pytanie dotyczące dokumentacji SWZ poniżej lub wybierz
              gotowe pytanie z menu „Szablony”.
            </div>
          ) : (
            <div className="chat-messages">
              {messages.map((msg, idx) => (
                <div key={idx} className="chat-msg">
                  <div className={`chat-bubble ${msg.role}`}>
                    {msg.role === "assistant" ? (
                      msg.text ? (
                        <MarkdownText text={msg.text} />
                      ) : (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 10,
                          }}
                        >
                          <span className="spinner dark" />
                          <span>
                            Przeszukuję dokumentację SWZ i generuję odpowiedź...
                          </span>
                        </div>
                      )
                    ) : (
                      msg.text
                    )}
                  </div>
                  {msg.role === "assistant" && msg.text && (
                    <div className="msg-actions">
                      <button
                        type="button"
                        className="text-action-btn"
                        onClick={() => handleCopy(msg.text, idx)}
                      >
                        <CopyIcon size={14} />
                        <span>
                          {copiedIdx === idx ? "Skopiowano" : "Kopiuj"}
                        </span>
                      </button>

                      {msg.chunks?.length > 0 && (
                        <button
                          type="button"
                          className="text-action-btn"
                          onClick={() =>
                            setOpenSources((prev) => ({
                              ...prev,
                              [idx]: !prev[idx],
                            }))
                          }
                        >
                          {openSources[idx]
                            ? `Ukryj źródła SWZ (${msg.chunks.length})`
                            : `Pokaż źródła SWZ (${msg.chunks.length})`}
                        </button>
                      )}
                    </div>
                  )}

                  {msg.role === "assistant" &&
                    openSources[idx] &&
                    msg.chunks?.length > 0 && (
                      <div className="sources-list">
                        {msg.chunks.map((c, cIdx) => (
                          <div key={cIdx} className="source-item">
                            <div className="source-item-head">
                              <span>{c.section_title || "Fragment SWZ"}</span>
                              <span className="tabular">
                                Trafność:{" "}
                                {Number(c.rerank_score || 0).toFixed(2)}
                              </span>
                            </div>
                            <div className="source-item-body">{c.content}</div>
                          </div>
                        ))}
                      </div>
                    )}
                </div>
              ))}

              <div ref={chatEndRef} />
            </div>
          )}
        </div>
      </div>

      <form className="composer-dock" onSubmit={handleSend}>
        <div className="composer-inner" ref={composerRef}>
          {templatesOpen && (
            <div
              className="templates-popover"
              role="listbox"
              aria-label="Szablony pytań SWZ"
            >
              {RAG_TEMPLATES.map((tpl, i) => (
                <button
                  key={i}
                  type="button"
                  className="template-option"
                  onClick={() => {
                    setQuestion(tpl);
                    setTemplatesOpen(false);
                  }}
                >
                  {tpl}
                </button>
              ))}
            </div>
          )}

          {questionQueue.length > 0 && (
            <div className="queue-strip" aria-label="Kolejka pytań">
              <div className="queue-strip-head">
                <span>Kolejka pytań ({questionQueue.length})</span>
                <button
                  type="button"
                  className="text-action-btn"
                  onClick={() => setQuestionQueue([])}
                >
                  Wyczyść kolejkę
                </button>
              </div>
              <div className="queue-items">
                {questionQueue.map((item, qIdx) => (
                  <div key={item.id} className="queue-chip" title={item.text}>
                    <span className="queue-chip-text">
                      {qIdx + 1}. {item.text}
                    </span>
                    <button
                      type="button"
                      className="queue-chip-remove"
                      onClick={() => handleRemoveQueued(item.id)}
                      aria-label={`Usuń pytanie z kolejki: ${item.text}`}
                      title="Usuń z kolejki"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <textarea
            className="composer-textarea"
            placeholder={
              asking
                ? "Generuję odpowiedź... Wpisz kolejne pytanie, aby dodać je do kolejki."
                : "Zadaj pytanie dotyczące dokumentacji SWZ..."
            }
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
          />

          <div className="composer-toolbar">
            <div className="composer-left">
              <button
                type="button"
                className="btn btn-secondary btn-compact"
                onClick={() => setTemplatesOpen((o) => !o)}
              >
                <SparklesIcon size={15} />
                <span>Szablony</span>
              </button>

              <span className="model-pill" title="Lokalny model analityczny">
                <span
                  className="status-dot"
                  style={{ color: "var(--success)" }}
                />
                Ollama · gis-analyst
              </span>

              <div
                className="segmented-control"
                role="group"
                aria-label="Format odpowiedzi"
              >
                {FORMAT_OPTIONS.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    className={`segmented-btn ${responseFormat === opt ? "active" : ""}`}
                    aria-pressed={responseFormat === opt}
                    onClick={() => setResponseFormat(opt)}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>

            <div className="composer-actions">
              {asking && (
                <button
                  type="button"
                  className="btn btn-compact btn-stop"
                  onClick={handleStopGeneration}
                  title="Zatrzymaj generowanie"
                  aria-label="Zatrzymaj generowanie"
                >
                  <span
                    aria-hidden="true"
                    style={{
                      display: "inline-block",
                      width: 10,
                      height: 10,
                      borderRadius: 2,
                      background: "currentColor",
                    }}
                  />
                  <span>Zatrzymaj</span>
                </button>
              )}

              <button
                type="submit"
                className="btn-icon primary"
                disabled={!question.trim()}
                title={asking ? "Dodaj pytanie do kolejki" : "Wyślij pytanie"}
                aria-label={
                  asking ? "Dodaj pytanie do kolejki" : "Wyślij pytanie"
                }
              >
                <SendIcon size={17} />
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}

function SettingsView({ user }) {
  const isAdmin = user.role === "admin";
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(isAdmin);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [passwords, setPasswords] = useState({});
  const [showPass, setShowPass] = useState({});
  const [confirmDelete, setConfirmDelete] = useState(null);

  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showNewPass, setShowNewPass] = useState(false);

  async function refreshUsers() {
    if (!isAdmin) return;
    setLoading(true);
    setError("");
    try {
      const list = await api.listUsers();
      setUsers(list.filter((u) => u.role !== "admin"));
    } catch (err) {
      setError(err.message || "Nie udało się pobrać listy użytkowników.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshUsers();
  }, [isAdmin]);

  if (!isAdmin) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div>
            <h1 className="page-title">Ustawienia</h1>
            <p className="page-subtitle">
              Informacje o Twoim koncie w systemie.
            </p>
          </div>
        </div>
        <div className="card spec-list">
          <div className="spec-row">
            <div className="spec-label">Login</div>
            <div className="spec-value">{user.username}</div>
          </div>
          <div className="spec-row">
            <div className="spec-label">Rola</div>
            <div className="spec-value">Użytkownik</div>
          </div>
          <div className="spec-row">
            <div className="spec-label">Status konta</div>
            <div className="spec-value">
              <span className="badge badge-green">
                <span className="status-dot" />
                Aktywne
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  async function handleSavePassword(username) {
    const pw = (passwords[username] || "").trim();
    if (pw.length < 6) {
      setError("Hasło musi mieć co najmniej 6 znaków.");
      return;
    }
    setError("");
    setNotice("");
    try {
      await api.updateUserPassword(username, pw);
      setPasswords((prev) => ({ ...prev, [username]: "" }));
      setNotice(`Zaktualizowano hasło użytkownika ${username}.`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleToggleActive(u) {
    setError("");
    setNotice("");
    try {
      await api.setUserActive(u.username, !u.is_active);
      setUsers((prev) =>
        prev.map((row) =>
          row.username === u.username
            ? { ...row, is_active: !u.is_active }
            : row,
        ),
      );
      setNotice(
        `Konto ${u.username} zostało ${!u.is_active ? "aktywowane" : "zablokowane"}.`,
      );
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(username) {
    setError("");
    setNotice("");
    try {
      await api.deleteUser(username);
      setUsers((prev) => prev.filter((row) => row.username !== username));
      setConfirmDelete(null);
      setNotice(`Usunięto konto ${username}.`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAddUser(e) {
    e.preventDefault();
    const u = newUsername.trim();
    if (!u || newPassword.length < 6) {
      setError("Podaj login oraz hasło (min. 6 znaków).");
      return;
    }
    setError("");
    setNotice("");
    try {
      const created = await api.createUser(u, newPassword);
      setUsers((prev) => [...prev, created]);
      setNewUsername("");
      setNewPassword("");
      setNotice(`Dodano pracownika ${created.username}.`);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Ustawienia</h1>
          <p className="page-subtitle">
            Zarządzanie kontami pracowników i uprawnieniami dostępu.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      <div className="card">
        <div className="admin-grid-row header">
          <div>LOGIN</div>
          <div>HASŁO</div>
          <div>AKCJE</div>
        </div>

        {loading ? (
          <div
            style={{
              padding: 20,
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <div className="skeleton" style={{ height: 40 }} />
            <div className="skeleton" style={{ height: 40 }} />
          </div>
        ) : (
          users.map((u) => (
            <div key={u.username} className="admin-grid-row">
              <div
                style={{
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span>{u.username}</span>
                {!u.is_active && (
                  <span className="badge badge-amber">Zablokowane</span>
                )}
              </div>

              <div className="password-wrap">
                <input
                  className="input"
                  type={showPass[u.username] ? "text" : "password"}
                  placeholder="Nowe hasło (min. 6 znaków)"
                  value={passwords[u.username] || ""}
                  onChange={(e) =>
                    setPasswords((prev) => ({
                      ...prev,
                      [u.username]: e.target.value,
                    }))
                  }
                />
                <button
                  type="button"
                  className="password-eye"
                  onClick={() =>
                    setShowPass((prev) => ({
                      ...prev,
                      [u.username]: !prev[u.username],
                    }))
                  }
                  aria-label="Pokaż lub ukryj hasło"
                >
                  {showPass[u.username] ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>

              <div className="action-icons">
                <button
                  type="button"
                  className="btn-icon primary"
                  title="Zapisz nowe hasło"
                  aria-label="Zapisz hasło"
                  disabled={!(passwords[u.username] || "").trim()}
                  onClick={() => handleSavePassword(u.username)}
                >
                  <SaveIcon />
                </button>

                <button
                  type="button"
                  className={`btn-icon ${u.is_active ? "active-green" : "inactive-amber"}`}
                  title={
                    u.is_active
                      ? "Odblokowane (kliknij, aby zablokować)"
                      : "Zablokowane (kliknij, aby odblokować)"
                  }
                  aria-label="Przełącz status blokady konta"
                  onClick={() => handleToggleActive(u)}
                >
                  {u.is_active ? <UnlockIcon /> : <LockIcon />}
                </button>

                {confirmDelete === u.username ? (
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 6 }}
                  >
                    <span
                      style={{
                        fontSize: 12,
                        color: "var(--danger)",
                        fontWeight: 600,
                      }}
                    >
                      Czy na pewno?
                    </span>
                    <button
                      type="button"
                      className="btn btn-danger-soft btn-compact"
                      onClick={() => handleDelete(u.username)}
                    >
                      Tak
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-compact"
                      onClick={() => setConfirmDelete(null)}
                    >
                      Nie
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="btn-icon danger"
                    title="Usuń konto"
                    aria-label="Usuń konto"
                    onClick={() => setConfirmDelete(u.username)}
                  >
                    <TrashIcon />
                  </button>
                )}
              </div>
            </div>
          ))
        )}

        <form className="admin-grid-row add-row" onSubmit={handleAddUser}>
          <input
            className="input"
            type="text"
            placeholder="Nowy login"
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
          />

          <div className="password-wrap">
            <input
              className="input"
              type={showNewPass ? "text" : "password"}
              placeholder="Hasło (min. 6 znaków)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <button
              type="button"
              className="password-eye"
              onClick={() => setShowNewPass((s) => !s)}
              aria-label="Pokaż lub ukryj hasło"
            >
              {showNewPass ? <EyeOffIcon /> : <EyeIcon />}
            </button>
          </div>

          <div className="action-icons">
            <button
              type="submit"
              className="btn-icon primary"
              title="Dodaj pracownika"
              aria-label="Dodaj pracownika"
            >
              <PlusIcon />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function AboutView() {
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getAbout()
      .then(setInfo)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">O programie</h1>
          <p className="page-subtitle">
            Architektura i bieżący status lokalnego systemu analityki SWZ.
          </p>
        </div>
      </div>

      {loading ? (
        <div
          className="card"
          style={{
            padding: 20,
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          <div className="skeleton" style={{ height: 36 }} />
          <div className="skeleton" style={{ height: 36 }} />
          <div className="skeleton" style={{ height: 36 }} />
        </div>
      ) : (
        <div className="card spec-list">
          <div className="spec-row">
            <div>
              <div className="spec-label">Indeksowanie semantyczne</div>
              <div className="spec-desc">
                Wyszukiwanie hybrydowe (Dense + Sparse + RRF)
              </div>
            </div>
            <div className="spec-value">
              {info?.embedding_model || "BGE-M3"} + pgvector
            </div>
          </div>

          <div className="spec-row">
            <div>
              <div className="spec-label">Reranking i weryfikacja</div>
              <div className="spec-desc">
                Kontrola ugruntowania odpowiedzi w źródłach SWZ
              </div>
            </div>
            <div className="spec-value">
              {info?.reranker_model || "bge-reranker-v2-m3"} · RAGAS ≥ 0.95
            </div>
          </div>

          <div className="spec-row">
            <div>
              <div className="spec-label">Lokalny model językowy (LLM)</div>
              <div className="spec-desc">
                Silnik wnioskowania na potrzeby streszczeń i czatu
              </div>
            </div>
            <div
              className="spec-value"
              style={{ display: "flex", alignItems: "center", gap: 10 }}
            >
              <span>Ollama · {info?.ollama_model || "gis-analyst"}</span>
              <span
                className={`badge ${info?.ollama_ok ? "badge-green" : "badge-red"}`}
              >
                <span className="status-dot" />
                {info?.ollama_ok ? "Online" : "Offline"}
              </span>
            </div>
          </div>

          <div className="spec-row">
            <div>
              <div className="spec-label">Zaindeksowane postępowania</div>
              <div className="spec-desc">
                Liczba postępowań gotowych do analizy w bazie
              </div>
            </div>
            <div className="spec-value tabular">
              {info?.total_tenders ?? 0} SWZ
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [authChecking, setAuthChecking] = useState(Boolean(getStoredToken()));
  const [route, setRoute] = useState("home");
  const [procurements, setProcurements] = useState([]);
  const [loadingProc, setLoadingProc] = useState(false);
  const [procError, setProcError] = useState("");
  const [selectedTender, setSelectedTender] = useState(null);
  const [summaryCache, setSummaryCache] = useState({});
  const [chatHistoryByTender, setChatHistoryByTender] = useState({});

  function handleCacheSummary(ocdsId, data) {
    setSummaryCache((prev) => ({ ...prev, [ocdsId]: data }));
  }

  function handleUpdateMessages(ocdsId, updater) {
    setChatHistoryByTender((prev) => {
      const current = prev[ocdsId] || [];
      const next = typeof updater === "function" ? updater(current) : updater;
      return { ...prev, [ocdsId]: next };
    });
  }

  useEffect(() => {
    const handleUnauth = () => {
      setUser(null);
      setSelectedTender(null);
      setRoute("home");
    };
    window.addEventListener("gm:unauthorized", handleUnauth);
    return () => window.removeEventListener("gm:unauthorized", handleUnauth);
  }, []);

  useEffect(() => {
    if (!getStoredToken()) {
      setAuthChecking(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => setStoredToken(""))
      .finally(() => setAuthChecking(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    setLoadingProc(true);
    setProcError("");
    api
      .listProcurements()
      .then(setProcurements)
      .catch((err) =>
        setProcError(err.message || "Nie udało się wczytać przetargów."),
      )
      .finally(() => setLoadingProc(false));
  }, [user]);

  function handleLogout() {
    setStoredToken("");
    setUser(null);
    setSelectedTender(null);
    setRoute("home");
  }

  function handleNavigate(nextRoute) {
    setRoute(nextRoute);
    if (nextRoute !== "detail") {
      setSelectedTender(null);
    }
  }

  if (authChecking) {
    return (
      <div className="login-shell">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            color: "var(--ink-secondary)",
          }}
        >
          <span className="spinner dark" />
          <span>Weryfikacja sesji...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginView onLogin={setUser} />;
  }

  return (
    <div className="app-shell">
      <Sidebar
        user={user}
        route={route}
        onNavigate={handleNavigate}
        onLogout={handleLogout}
      />

      <main className="main-area">
        {route === "detail" && selectedTender ? (
          <TenderDetailView
            tender={selectedTender}
            cachedSummary={summaryCache[selectedTender.id] || null}
            onCacheSummary={handleCacheSummary}
            messages={chatHistoryByTender[selectedTender.id] || []}
            onUpdateMessages={handleUpdateMessages}
            onBack={() => handleNavigate("home")}
          />
        ) : route === "settings" ? (
          <SettingsView user={user} />
        ) : route === "about" ? (
          <AboutView />
        ) : (
          <HomeView
            procurements={procurements}
            loading={loadingProc}
            error={procError}
            onOpenTender={(item) => {
              setSelectedTender(item);
              setRoute("detail");
            }}
          />
        )}
      </main>
    </div>
  );
}
