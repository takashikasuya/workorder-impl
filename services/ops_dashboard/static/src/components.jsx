/* Shell components: Rail (left nav), TopBar, KPI strip, FilterBar, Manifesto */

const { useState, useEffect } = React;

/* ------- tiny inline icons (no library) ------- */
function Icon({ name, size = 14 }) {
  const s = size, sw = 1.6;
  const common = {
    width: s, height: s, viewBox: "0 0 24 24",
    fill: "none", stroke: "currentColor",
    strokeWidth: sw, strokeLinecap: "round", strokeLinejoin: "round",
  };
  switch (name) {
    case "home":     return <svg {...common}><path d="M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1V11z"/></svg>;
    case "flow":     return <svg {...common}><path d="M4 6h6M14 6h6M4 12h6M14 12h6M4 18h6M14 18h6"/></svg>;
    case "alert":    return <svg {...common}><path d="M12 9v4M12 17h.01M10.3 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>;
    case "queue":    return <svg {...common}><path d="M5 4h14M5 10h14M5 16h14M5 22h14"/></svg>;
    case "calendar": return <svg {...common}><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>;
    case "settings": return <svg {...common}><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.6-2-3.5-2.4.9a7 7 0 0 0-2-1.2L14 3h-4l-.5 2.4a7 7 0 0 0-2 1.2l-2.4-.9-2 3.5 2 1.6A7 7 0 0 0 5 12a7 7 0 0 0 .1 1.2l-2 1.6 2 3.5 2.4-.9a7 7 0 0 0 2 1.2L10 21h4l.5-2.4a7 7 0 0 0 2-1.2l2.4.9 2-3.5-2-1.6c.07-.4.1-.8.1-1.2z"/></svg>;
    case "search":   return <svg {...common}><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>;
    case "filter":   return <svg {...common}><path d="M22 3H2l8 9.5V19l4 2v-8.5L22 3z"/></svg>;
    case "x":        return <svg {...common}><path d="m6 6 12 12M6 18 18 6"/></svg>;
    case "chev":     return <svg {...common}><path d="m9 18 6-6-6-6"/></svg>;
    case "down":     return <svg {...common}><path d="m6 9 6 6 6-6"/></svg>;
    case "person":   return <svg {...common}><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>;
    case "sensor":   return <svg {...common}><path d="M2 12h3M19 12h3M12 2v3M12 19v3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/><circle cx="12" cy="12" r="3"/></svg>;
    case "clock":    return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>;
    case "pin":      return <svg {...common}><path d="M12 22s7-7.5 7-13a7 7 0 0 0-14 0c0 5.5 7 13 7 13z"/><circle cx="12" cy="9" r="2.5"/></svg>;
    case "info":     return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5h1"/></svg>;
    case "check":    return <svg {...common}><path d="m5 12 5 5 9-11"/></svg>;
    case "external": return <svg {...common}><path d="M14 3h7v7M21 3l-9 9M5 5h6M5 11v8h14v-6"/></svg>;
    case "arrow":    return <svg {...common}><path d="M5 12h14M13 6l6 6-6 6"/></svg>;
    case "moon":     return <svg {...common}><path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/></svg>;
    case "sun":      return <svg {...common}><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>;
    case "plus":     return <svg {...common}><path d="M12 5v14M5 12h14"/></svg>;
    case "wrench":   return <svg {...common}><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>;
    default: return null;
  }
}

/* ------- Left navigation rail ------- */
function Rail({ active, onChange, counts }) {
  return (
    <aside className="rail">
      <div className="rail-brand">
        <div className="rail-brand-mark">OPS</div>
        <div className="rail-brand-text">
          <span className="name">FM Ops Console</span>
          <span className="id">CS-OPS-DASHBOARD</span>
        </div>
      </div>

      <div className="rail-section">運用</div>
      <RailItem id="overview" label="Overview" icon="home"
                active={active} onChange={onChange} />
      <RailItem id="flows"    label="フロー一覧" icon="flow" badge={counts.allFlows}
                active={active} onChange={onChange} />
      <RailItem id="problems" label="問題キュー" icon="alert" badge={counts.problems}
                active={active} onChange={onChange} problem />
      <RailItem id="reports"  label="Report 評価" icon="queue" badge={counts.reportQueue}
                active={active} onChange={onChange} />

      <div className="rail-section">操作</div>
      <RailItem id="tasks" label="タスク登録" icon="wrench"
                active={active} onChange={onChange} />

      <div className="rail-section">設定</div>
      <RailItem id="schedules" label="予防保全スケジュール" icon="calendar"
                active={active} onChange={onChange} />
      <RailItem id="settings"  label="ダッシュボード設定" icon="settings"
                active={active} onChange={onChange} />

      <div className="rail-spacer" />
      <div className="rail-foot">
        <div>FM管理者ロール</div>
        <div className="mono" style={{ color: "var(--c-text-4)" }}>
          BFF: IF-OPS-001 v0.3.0
        </div>
      </div>
    </aside>
  );
}
function RailItem({ id, label, icon, badge, active, onChange, problem }) {
  return (
    <div className={"rail-item" + (problem ? " is-problem" : "")}
         role="button"
         tabIndex={0}
         aria-current={active === id}
         onClick={() => onChange(id)}
         onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onChange(id); } }}>
      <Icon name={icon} />
      <span>{label}</span>
      {badge != null && <span className="badge num">{badge}</span>}
    </div>
  );
}

/* ------- Top bar ------- */
function TopBar({ onOpenManifesto, scope, onToggleTheme, theme, query, onQuery }) {
  return (
    <header className="topbar">
      <div className="crumbs">
        <span>SOI-WOM</span>
        <span className="sep">/</span>
        <span>CS-OPS-DASHBOARD</span>
        <span className="sep">/</span>
        <strong>{scope}</strong>
      </div>

      <div className="search">
        <Icon name="search" size={13} />
        <input
          placeholder="フロー / Issue ID / Ticket / 担当者を検索…"
          value={query}
          onChange={e => onQuery(e.target.value)}
        />
        {query
          ? <button
              style={{ background: "none", border: "none", cursor: "pointer",
                       color: "var(--c-text-3)", padding: "0 2px", lineHeight: 1 }}
              onClick={() => onQuery("")}
              aria-label="検索クリア">
              <Icon name="x" size={12} />
            </button>
          : <span className="kbd">⌘K</span>}
      </div>

      <div className="filler" />

      <button className="topbar-pill" title="集約データソース">
        <span className="dot" />
        <span>6 CS API live</span>
      </button>
      <button className="topbar-pill" onClick={onToggleTheme} aria-label="テーマ切替">
        <Icon name={theme === "dark" ? "sun" : "moon"} size={13} />
        <span>{theme === "dark" ? "Light" : "Dark"}</span>
      </button>
      <button className="topbar-pill" onClick={onOpenManifesto}>
        <Icon name="info" size={13} />
        <span>UX 提言</span>
      </button>
    </header>
  );
}

/* ------- KPI tiles ------- */
function KPIBar({ items, selected, onSelect }) {
  return (
    <div className="kpis">
      {items.map(k => {
        const tone = (window.PROBLEM_TYPES[k.key] || {}).tone || "info";
        return (
          <button key={k.key}
                  className={"kpi " + tone}
                  aria-current={selected === k.key}
                  onClick={() => onSelect(selected === k.key ? null : k.key)}>
            <span className="stripe" />
            <span className="label">{k.label}</span>
            <span className="row">
              <span className="count">{k.count}</span>
              <span className={"trend " + (k.trend.startsWith("+") ? "up" : k.trend === "0" ? "" : "down")}>
                {k.trend === "0" ? "—" : k.trend} 24h
              </span>
            </span>
            <span className="desc">{k.desc}</span>
          </button>
        );
      })}
    </div>
  );
}

/* ------- Filter bar with primary tabs ------- */
function FilterBar({ tab, onTab, tabs, filters, onFilter, showAdv, onToggleAdv, advFilters, onAdvFilter, onClearAdv }) {
  const advPriorities = ["P1", "P2", "P3"];
  const advPeriods    = ["今日", "今週", "今月"];
  const advOrigins    = [
    { key: "report",   label: "Report" },
    { key: "iot",      label: "IoTEvent" },
    { key: "schedule", label: "スケジュール" },
  ];
  const advActiveCount = advFilters
    ? [advFilters.priority, advFilters.period, advFilters.origin].filter(Boolean).length
    : 0;

  return (
    <div>
      <div className="filter-bar">
        <div className="tabs">
          {tabs.map(t =>
            <button key={t.key}
                    className="tab"
                    aria-pressed={tab === t.key}
                    onClick={() => onTab(t.key)}>
              <span>{t.label}</span>
              <span className="count num">{t.count}</span>
            </button>
          )}
        </div>

        <div style={{ width: 12 }} />

        <FilterChip label="ビル" value={filters.building} onClear={() => onFilter("building", null)} />
        <FilterChip label="種別" value={filters.entity}   onClear={() => onFilter("entity", null)} />
        <FilterChip label="期間" value={filters.range || "直近 7日"} />
        <FilterChip label="担当" value={filters.agent}    onClear={() => onFilter("agent", null)} />

        <div className="filler" style={{ flex: 1 }} />

        <button className={"filter-chip" + (showAdv ? " is-active" : "")}
                onClick={onToggleAdv}>
          <Icon name="filter" size={12} />
          詳細フィルタ
          {advActiveCount > 0 && (
            <span style={{
              background: "var(--c-primary)", color: "#fff", borderRadius: "50%",
              width: 16, height: 16, fontSize: 10, display: "inline-flex",
              alignItems: "center", justifyContent: "center", marginLeft: 2,
            }}>{advActiveCount}</span>
          )}
        </button>
      </div>

      {showAdv && (
        <div style={{
          padding: "10px 16px", background: "var(--c-surface-2,var(--c-surface))",
          borderBottom: "1px solid var(--c-border)",
          display: "flex", gap: 20, flexWrap: "wrap", alignItems: "center",
        }}>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "var(--c-text-3)", minWidth: 36 }}>優先度</span>
            {advPriorities.map(p => (
              <button key={p}
                      className={"filter-chip" + (advFilters?.priority === p ? " is-active" : "")}
                      onClick={() => onAdvFilter("priority", p)}>
                {p}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "var(--c-text-3)", minWidth: 36 }}>更新</span>
            {advPeriods.map(p => (
              <button key={p}
                      className={"filter-chip" + (advFilters?.period === p ? " is-active" : "")}
                      onClick={() => onAdvFilter("period", p)}>
                {p}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "var(--c-text-3)", minWidth: 36 }}>起源</span>
            {advOrigins.map(o => (
              <button key={o.key}
                      className={"filter-chip" + (advFilters?.origin === o.key ? " is-active" : "")}
                      onClick={() => onAdvFilter("origin", o.key)}>
                {o.label}
              </button>
            ))}
          </div>
          {advActiveCount > 0 && (
            <button style={{
              marginLeft: "auto", fontSize: 11, color: "var(--c-text-3)",
              background: "none", border: "none", cursor: "pointer", padding: "4px 8px",
            }}
                    onClick={onClearAdv}>
              クリア
            </button>
          )}
        </div>
      )}
    </div>
  );
}
function FilterChip({ label, value, onClear }) {
  const active = value && value !== "All" && value !== "—";
  return (
    <button className={"filter-chip" + (active ? " is-active" : "")}>
      <span>{label}:</span>
      <strong>{value || "All"}</strong>
      {active && onClear && (
        <span onClick={(e) => { e.stopPropagation(); onClear(); }} style={{ display: "inline-flex" }}>
          <Icon name="x" size={11} />
        </span>
      )}
      {!active && <Icon name="down" size={11} />}
    </button>
  );
}

/* ------- Manifesto overlay (the "UX proposal") ------- */
function Manifesto({ open, onClose }) {
  return (
    <div className={"manifesto-scrim" + (open ? " open" : "")} onClick={onClose}>
      <div className="manifesto" onClick={e => e.stopPropagation()}>
        <h2>CS-OPS-DASHBOARD のあるべきUI</h2>
        <p className="lede">
          ISO/IEC/IEEE 15288 に従って 10 CS が <code>Report/IoTEvent → Issue → Ticket → WorkOrder → Payment</code>{" "}
          の業務連鎖を構成する SoS。本 BFF は <strong>IF-OPS-001</strong> を介して 6つのCSのAPIを集約し、データ自身は保持しない。
          したがって UI 設計の核は「分散した状態機械をどう <em>横断俯瞰</em> させ、どう <em>トリアージ</em> させるか」。
        </p>

        <h3>5つの設計原則</h3>
        <div className="princ-grid">
          <div className="princ">
            <div className="n">01</div>
            <h4>Problem-first, not list-first</h4>
            <p>
              FM管理者の主作業は <code>pending_review</code> / <code>conflicted</code> / 滞留 / 精算未完了の<strong>消し込み</strong>。
              一覧ではなく、問題キューを起点に常設する（FUN-OPS-001 の "問題状態にフラグ付与" を最上段に昇格）。
            </p>
          </div>
          <div className="princ">
            <div className="n">02</div>
            <h4>Chain as the unit of attention</h4>
            <p>
              SoS の本質は「鎖」。1行 = 1つの起点から現在状態までのチェーン。
              5ノード（OBS / ISS / TKT / WO / PAY）を常時可視化し、どこで止まっているかを <strong>1秒</strong> で読ませる。
            </p>
          </div>
          <div className="princ">
            <div className="n">03</div>
            <h4>Action lives next to evidence</h4>
            <p>
              <code>POST /ops/actions</code> の転送先は IF-ISSUE-001 / IF-OBS-002 / IF-WO-001 / IF-TICKET-001 と分散している。
              UI 側ではタイムライン（証跡）と隣接させ、<strong>同じドロワー</strong>で確定・却下・再アサインを完結させる。
            </p>
          </div>
          <div className="princ">
            <div className="n">04</div>
            <h4>State machines, made literal</h4>
            <p>
              Booking が conflicted でも WO 発行は止めない（REQ-SOS-009）／緊急WO は Estimate を飛ばす（REQ-SOS-015）。
              "例外" を別画面に追いやらず、同じチェーン UI 上で<strong>異常分岐</strong>として並べる。
            </p>
          </div>
          <div className="princ">
            <div className="n">05</div>
            <h4>BFF is read-aggregator, not master</h4>
            <p>
              ダッシュボードはデータの正本ではない。UI 上の各 ID 表示は対応 CS の詳細 API への<strong>素通し</strong>として
              位置付け、誤って "二重真実" にしない。各セルから IF へのリンクを明示。
            </p>
          </div>
        </div>

        <h3>情報アーキテクチャ</h3>
        <ol>
          <li><strong>左レール</strong>: Overview / フロー / 問題キュー / Report評価 / 予防保全スケジュール / 設定</li>
          <li><strong>問題 KPI 帯（6枚）</strong>: クリックで該当キューに絞り込み（Report滞留 / NonStdレビュー / 見積承認待ち / Booking競合 / 期限超過 / 緊急WO精算未完了）</li>
          <li><strong>主タブ</strong>: <code>すべて</code> / <code>問題のみ</code> / <code>Report評価</code> / <code>緊急精算</code> ／ ビル・期間・担当のチップ</li>
          <li><strong>Chain Table</strong>: 1行＝1フロー。優先度・タイトル・5ノードチェーン・問題タグ・最終更新</li>
          <li><strong>詳細ドロワー</strong>: 縦型チェーン + 状態遷移タイムライン + 当該CSへの管理操作カード</li>
        </ol>

        <h3>意識して外したもの</h3>
        <ul>
          <li>派手なグラフダッシュボード（運用は数字ではなく "次の1件" を求めている）</li>
          <li>左ナビからの深いツリー（鎖の方が CS の境界より大事）</li>
          <li>Issue 単位・Ticket 単位の独立ページ（CS のWeb UI の責務、本BFF はリンクで委譲）</li>
        </ul>

        <div className="manifesto-foot">
          <button className="btn primary" onClick={onClose}>了解、ダッシュボードへ</button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Icon, Rail, TopBar, KPIBar, FilterBar, Manifesto });
