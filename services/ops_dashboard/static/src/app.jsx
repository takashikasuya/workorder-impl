/* CS-OPS-DASHBOARD — main app */

const { useState, useEffect, useMemo, useCallback } = React;

function transformBffFlows(bffFlows) {
  return bffFlows.map(bff => {
    const issue = bff.issue || {};
    const ticket = bff.tickets?.[0];
    const wo = bff.work_orders?.[0];
    const payment = bff.payments?.[0];
    const origin = issue.derived_from_type === "IoTEvent" ? "iot"
                 : issue.derived_from_type === "Report"   ? "report"
                 : "schedule";
    const issueStatus = { Open: "open", PendingReview: "pending_review",
                          UnderReview: "open", Resolved: "closed" }[issue.issue_status] || "open";
    const woStatus = { Open: "wo_open", InProgress: "wo_in_progress",
                       Completed: "wo_completed" }[wo?.work_order_status] || "wo_open";
    const problem = bff.problem_flags?.[0] || "none";
    return {
      id: issue.issue_id,
      priority: "P2",
      origin,
      building: null, floor: null, space: null,
      title: issue.title || "(無題)",
      woType: wo?.work_order_type || null,
      issueType: issue.issue_type || null,
      openedAt: issue.detected_at || new Date().toISOString(),
      updatedAt: issue.detected_at || new Date().toISOString(),
      problem,
      note: issue.description || null,
      chain: [
        { kind: "observation", id: issue.derived_from_id || null,
          status: origin === "report" ? "report_approved" : origin === "iot" ? "iot_received" : "not_started",
          label: origin === "report" ? "Report" : origin === "iot" ? "IoTEvent" : "—" },
        { kind: "issue", id: issue.issue_id, status: issueStatus, label: "Issue" },
        { kind: "ticket", id: ticket?.ticket_id || null,
          status: ticket ? "estimate_approved" : "not_started", label: "Ticket" },
        { kind: "workorder", id: wo?.work_order_id || null,
          status: wo ? woStatus : "not_started", label: "WO" },
        { kind: "payment", id: payment?.payment_id || null,
          status: payment ? "pay_paid" : "not_started", label: "Pay" },
      ],
      timeline: [],
      isLive: true,
    };
  });
}

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "density": "comfortable",
  "theme": "light",
  "primary_view": "chain",
  "accent": "#3b5cdb"
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = window.useTweaks(TWEAK_DEFAULTS);
  const [liveFlows, setLiveFlows]     = useState([]);
  const [nav, setNav]                 = useState("flows");
  const [tab, setTab]                 = useState("all");
  const [kpi, setKpi]                 = useState(null);
  const [query, setQuery]             = useState("");
  const [filters, setFilters]         = useState({ building: null, entity: null, agent: null, range: "直近 7日" });
  const [selected, setSelected]       = useState(null);
  const [drawerOpen, setDrawerOpen]   = useState(false);
  const [manifestoOpen, setManifesto] = useState(() => {
    try { return localStorage.getItem("ops_manifesto_seen") !== "1"; }
    catch { return true; }
  });
  const closeManifesto = () => {
    try { localStorage.setItem("ops_manifesto_seen", "1"); } catch {}
    setManifesto(false);
  };
  const [theme, setTheme]             = useState(t.theme || "light");

  useEffect(() => { setTheme(t.theme || "light"); }, [t.theme]);

  const fetchLiveFlows = useCallback(() => {
    fetch("/ops/flows")
      .then(r => r.ok ? r.json() : { flows: [] })
      .then(data => setLiveFlows(transformBffFlows(data.flows || [])))
      .catch(() => {});
  }, []);

  useEffect(() => { fetchLiveFlows(); }, [fetchLiveFlows]);

  const allFlows = useMemo(() => [...liveFlows, ...window.FLOWS], [liveFlows]);

  /* Filter pipeline */
  const filteredFlows = useMemo(() => {
    let xs = allFlows.slice();

    if (tab === "problems") xs = xs.filter(f => f.problem && f.problem !== "none");
    if (tab === "reports")  xs = xs.filter(f => f.origin === "report" && (f.problem === "stale_report" || f.chain[0].status === "report_pending"));
    if (tab === "emergency_settlement") xs = xs.filter(f => f.problem === "unsettled");

    if (kpi) xs = xs.filter(f => f.problem === kpi);

    if (filters.building) xs = xs.filter(f => f.building === filters.building);

    if (query.trim()) {
      const q = query.trim().toLowerCase();
      xs = xs.filter(f =>
        f.title.toLowerCase().includes(q) ||
        f.id.toLowerCase().includes(q) ||
        (f.space || "").toLowerCase().includes(q) ||
        (f.floor || "").toLowerCase().includes(q) ||
        f.chain.some(c => (c.id || "").toLowerCase().includes(q))
      );
    }

    // sort: problems first (danger > warn > info > ok), then by updated desc
    const toneOrder = { danger: 0, warn: 1, info: 2, ok: 3 };
    xs.sort((a, b) => {
      const ta = (window.PROBLEM_TYPES[a.problem] || { tone: "ok" }).tone;
      const tb = (window.PROBLEM_TYPES[b.problem] || { tone: "ok" }).tone;
      if (toneOrder[ta] !== toneOrder[tb]) return toneOrder[ta] - toneOrder[tb];
      return new Date(b.updatedAt) - new Date(a.updatedAt);
    });
    return xs;
  }, [tab, kpi, filters, query]);

  /* Counts */
  const counts = useMemo(() => ({
    allFlows: allFlows.length,
    problems: allFlows.filter(f => f.problem && f.problem !== "none").length,
    reportQueue: allFlows.filter(f => f.origin === "report" && f.chain[0]?.status === "report_pending").length,
    emergency: allFlows.filter(f => f.problem === "unsettled").length,
  }), [allFlows]);

  const tabs = [
    { key: "all",      label: "すべて",         count: counts.allFlows },
    { key: "problems", label: "問題のみ",       count: counts.problems },
    { key: "reports",  label: "Report 評価",   count: counts.reportQueue },
    { key: "emergency_settlement", label: "緊急精算", count: counts.emergency },
  ];

  const selectedFlow = useMemo(() =>
    allFlows.find(f => f.id === selected), [selected, allFlows]);

  const onSelectFlow = (id) => {
    setSelected(id);
    setDrawerOpen(true);
  };

  const onToggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setTweak("theme", next);
  };

  const onFilter = (key, val) => setFilters(f => ({ ...f, [key]: val }));

  /* Scope label for breadcrumb */
  const scope =
    nav === "problems"  ? "問題キュー" :
    nav === "reports"   ? "Report 評価キュー" :
    nav === "schedules" ? "予防保全スケジュール" :
    nav === "settings"  ? "設定" :
    nav === "overview"  ? "Overview" :
    nav === "tasks"     ? "タスク登録" :
                          "業務フロー";

  return (
    <div className="app"
         data-theme={theme}
         data-density={t.density || "comfortable"}>

      <window.Rail active={nav}
                   onChange={setNav}
                   counts={counts} />

      <window.TopBar onOpenManifesto={() => setManifesto(true)}
                     scope={scope}
                     theme={theme}
                     onToggleTheme={onToggleTheme}
                     query={query}
                     onQuery={setQuery} />

      {nav === "tasks" && (
        <main className="main">
          <window.TaskPanel />
        </main>
      )}

      {nav === "overview" && (
        <main className="main">
          <OverviewPanel counts={counts} allFlows={allFlows} />
        </main>
      )}

      {nav !== "tasks" && nav !== "overview" && <main className="main">
        <div className="page-header">
          <div className="page-title">
            <h1>業務フロー監視</h1>
            <p>
              Report / IoTEvent → Issue → Ticket → WorkOrder → Payment の
              チェーン状態を6つのCSから集約。問題があるものから対応してください。
            </p>
          </div>
          <div className="page-actions">
            <span style={{
              fontSize: 11.5, color: "var(--c-text-3)", marginRight: 6,
            }}>
              現在時刻 <span className="mono">2026-05-17 10:00</span> · 30秒ごとに自動更新
            </span>
            <button className="btn ghost">
              <Icon name="external" size={12} /> CSV
            </button>
            <button className="btn primary">
              <Icon name="check" size={12} /> 全レビュー対象を一括処理
            </button>
          </div>
        </div>

        <window.KPIBar items={window.PROBLEM_KPIS}
                       selected={kpi}
                       onSelect={setKpi} />

        <window.FilterBar tab={tab}
                          onTab={setTab}
                          tabs={tabs}
                          filters={filters}
                          onFilter={onFilter} />

        <div className="flow-table">
          {filteredFlows.length === 0 ? (
            <EmptyState />
          ) : (
            filteredFlows.map(f =>
              <window.FlowRow key={f.id}
                              flow={f}
                              selected={selected === f.id}
                              onSelect={onSelectFlow} />
            )
          )}
        </div>
      </main>}

      <window.DetailDrawer flow={selectedFlow}
                           open={drawerOpen}
                           onClose={() => setDrawerOpen(false)}
                           onActionDone={() => fetchLiveFlows()} />

      <window.Manifesto open={manifestoOpen}
                        onClose={closeManifesto} />

      {/* Tweaks panel */}
      <window.TweaksPanel title="Tweaks">
        <window.TweakSection label="表示" />
        <window.TweakRadio
          label="密度"
          value={t.density}
          options={[
            { value: "comfortable", label: "Comfort" },
            { value: "compact",     label: "Compact" },
          ]}
          onChange={(v) => setTweak("density", v)}
        />
        <window.TweakRadio
          label="テーマ"
          value={t.theme}
          options={[
            { value: "light", label: "Light" },
            { value: "dark",  label: "Dark"  },
          ]}
          onChange={(v) => { setTweak("theme", v); setTheme(v); }}
        />

        <window.TweakSection label="主ビュー" />
        <window.TweakRadio
          label="FlowRow 構成"
          value={t.primary_view}
          options={[
            { value: "chain",  label: "Chain" },
            { value: "kanban", label: "Kanban" },
          ]}
          onChange={(v) => setTweak("primary_view", v)}
        />

        <window.TweakSection label="クイックアクション" />
        <window.TweakButton label="UX 提言を再表示"
                            onClick={() => setManifesto(true)} />
        <window.TweakButton label="フィルタをリセット"
                            secondary
                            onClick={() => { setKpi(null); setTab("all"); setFilters({ building: null, entity: null, agent: null, range: "直近 7日" }); }} />
      </window.TweaksPanel>
    </div>
  );
}

function OverviewPanel({ counts, allFlows }) {
  const flows = allFlows || window.FLOWS;
  const byBuilding = window.BUILDINGS.map(b => ({
    ...b,
    total: flows.filter(f => f.building === b.id).length,
    problems: flows.filter(f => f.building === b.id && f.problem && f.problem !== "none").length,
  }));
  const byOrigin = ["report", "iot", "schedule"].map(o => ({
    key: o,
    ...window.ORIGIN_META[o],
    count: flows.filter(f => f.origin === o).length,
  }));
  const kpiBreakdown = window.PROBLEM_KPIS.map(k => ({
    ...k,
    tone: (window.PROBLEM_TYPES[k.key] || {}).tone || "info",
  }));

  const cell = { padding: "10px 14px", borderBottom: "1px solid var(--c-border)", fontSize: 13 };
  const statCard = (label, value, sub, tone) => {
    const bg = { danger: "var(--c-danger-bg,#fff0f0)", warn: "var(--c-warn-bg,#fffbeb)",
                 ok: "var(--c-ok-bg,#f0fff4)", info: "var(--c-info-bg,#ebf8ff)" }[tone] || "var(--c-surface)";
    const col = { danger: "var(--c-danger,#e53e3e)", warn: "var(--c-warn,#d97706)",
                  ok: "var(--c-ok,#38a169)", info: "var(--c-info,#2b6cb0)" }[tone] || "var(--c-text)";
    return (
      <div style={{ background: bg, border: `1px solid ${col}22`, borderRadius: 10,
                    padding: "14px 18px", minWidth: 120 }}>
        <div style={{ fontSize: 11, color: "var(--c-text-3)", marginBottom: 4 }}>{label}</div>
        <div style={{ fontSize: 28, fontWeight: 700, color: col, lineHeight: 1 }}>{value}</div>
        {sub && <div style={{ fontSize: 11, color: "var(--c-text-3)", marginTop: 4 }}>{sub}</div>}
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "0 24px 48px" }}>
      <div className="page-header" style={{ paddingTop: 0 }}>
        <div className="page-title">
          <h1>Overview</h1>
          <p>全フローの状態サマリー。問題のあるフローから対応してください。</p>
        </div>
      </div>

      {/* 大まかな件数 */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 28 }}>
        {statCard("監視中フロー", flows.length, "全チェーン", "info")}
        {statCard("要対応", counts.problems, "問題フラグあり", "warn")}
        {statCard("Report 評価待ち", counts.reportQueue, "未評価 Report", "warn")}
        {statCard("正常", flows.filter(f => !f.problem || f.problem === "none").length, "問題なし", "ok")}
      </div>

      {/* 問題種別内訳 */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: "var(--c-text)" }}>問題種別</div>
        <table style={{ width: "100%", borderCollapse: "collapse",
                        background: "var(--c-surface)", borderRadius: 10, overflow: "hidden",
                        border: "1px solid var(--c-border)" }}>
          <thead>
            <tr style={{ background: "var(--c-surface-2,var(--c-surface))" }}>
              {["種別", "件数", "傾向", "説明"].map(h =>
                <th key={h} style={{ ...cell, fontWeight: 600, fontSize: 11,
                                     color: "var(--c-text-3)", textAlign: "left" }}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {kpiBreakdown.map(k => {
              const dot = { danger: "#e53e3e", warn: "#d97706", info: "#2b6cb0", ok: "#38a169" }[k.tone] || "#999";
              return (
                <tr key={k.key}>
                  <td style={cell}>
                    <span style={{ display: "inline-block", width: 8, height: 8,
                                   borderRadius: "50%", background: dot, marginRight: 8 }} />
                    {k.label}
                  </td>
                  <td style={{ ...cell, fontWeight: 700 }}>{k.count}</td>
                  <td style={{ ...cell, color: k.trend?.startsWith("+") ? "#e53e3e" : "var(--c-text-3)" }}>
                    {k.trend ? `${k.trend} 24h` : "—"}
                  </td>
                  <td style={{ ...cell, color: "var(--c-text-3)", fontSize: 12 }}>{k.desc}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* ビル別 */}
        <div>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: "var(--c-text)" }}>ビル別</div>
          <table style={{ width: "100%", borderCollapse: "collapse",
                          background: "var(--c-surface)", borderRadius: 10, overflow: "hidden",
                          border: "1px solid var(--c-border)" }}>
            <thead>
              <tr style={{ background: "var(--c-surface-2,var(--c-surface))" }}>
                {["ビル", "合計", "要対応"].map(h =>
                  <th key={h} style={{ ...cell, fontWeight: 600, fontSize: 11,
                                       color: "var(--c-text-3)", textAlign: "left" }}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {byBuilding.map(b => (
                <tr key={b.id}>
                  <td style={cell}>{b.name}</td>
                  <td style={{ ...cell, fontWeight: 600 }}>{b.total}</td>
                  <td style={{ ...cell, color: b.problems > 0 ? "#d97706" : "var(--c-text-3)",
                               fontWeight: b.problems > 0 ? 700 : 400 }}>
                    {b.problems > 0 ? b.problems : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 起源別 */}
        <div>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: "var(--c-text)" }}>起源別</div>
          <table style={{ width: "100%", borderCollapse: "collapse",
                          background: "var(--c-surface)", borderRadius: 10, overflow: "hidden",
                          border: "1px solid var(--c-border)" }}>
            <thead>
              <tr style={{ background: "var(--c-surface-2,var(--c-surface))" }}>
                {["起源", "件数"].map(h =>
                  <th key={h} style={{ ...cell, fontWeight: 600, fontSize: 11,
                                       color: "var(--c-text-3)", textAlign: "left" }}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {byOrigin.map(o => (
                <tr key={o.key}>
                  <td style={cell}>{o.label}</td>
                  <td style={{ ...cell, fontWeight: 600 }}>{o.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div style={{
      padding: "60px 20px",
      textAlign: "center",
      color: "var(--c-text-3)",
    }}>
      <div style={{ fontSize: 14, fontWeight: 600, color: "var(--c-text)", marginBottom: 6 }}>
        対象のフローはありません
      </div>
      <div style={{ fontSize: 12 }}>
        フィルタ条件を緩めるか、KPI タイルを再選択してください。
      </div>
    </div>
  );
}

window.App = App;
ReactDOM.createRoot(document.getElementById("root")).render(<App />);
