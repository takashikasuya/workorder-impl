/* schedule-page.jsx — 予防保全スケジュール (nav=schedules) */

const { useState: useSchedState, useEffect: useSchedEffect } = React;

const WO_STATUS_COLOR = {
  Open:       "#3b5cdb",
  InProgress: "#d97706",
  Completed:  "#38a169",
};
const WO_STATUS_LABEL = {
  Open:       "Open",
  InProgress: "進行中",
  Completed:  "完了",
};

function SchedulePage() {
  const [wos, setWos]         = useSchedState([]);
  const [loading, setLoading] = useSchedState(true);
  const [filter, setFilter]   = useSchedState("all"); // "all" | "preventive" | "open"

  useSchedEffect(() => {
    fetch("/ops/work-orders")
      .then(r => r.ok ? r.json() : [])
      .then(data => { setWos(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const preventiveCount = wos.filter(w => w.work_order_type === "予防保全").length;
  const openCount       = wos.filter(w => w.work_order_status === "Open").length;

  const displayed = wos.filter(w => {
    if (filter === "preventive") return w.work_order_type === "予防保全";
    if (filter === "open")       return w.work_order_status === "Open";
    return true;
  });

  const cell = {
    padding: "10px 14px", fontSize: 13,
    borderBottom: "1px solid var(--c-border)",
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "0 24px 48px" }}>
      <div className="page-header" style={{ paddingTop: 0 }}>
        <div className="page-title">
          <h1>予防保全スケジュール</h1>
          <p>WorkOrder の一覧。予防保全タイプや未着手のものを確認できます。</p>
        </div>
      </div>

      <div className="filter-bar" style={{ marginBottom: 16 }}>
        <div className="tabs">
          {[
            { key: "all",        label: "すべて",    count: wos.length },
            { key: "preventive", label: "予防保全",  count: preventiveCount },
            { key: "open",       label: "Open",      count: openCount },
          ].map(t => (
            <button key={t.key}
                    className="tab"
                    aria-pressed={filter === t.key}
                    onClick={() => setFilter(t.key)}>
              <span>{t.label}</span>
              <span className="count num">{t.count}</span>
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: "var(--c-text-3)", fontSize: 13 }}>
          読み込み中…
        </div>
      ) : displayed.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", color: "var(--c-text-3)", fontSize: 13 }}>
          該当する WorkOrder はありません。
        </div>
      ) : (
        <table style={{
          width: "100%", borderCollapse: "collapse",
          background: "var(--c-surface)", borderRadius: 10, overflow: "hidden",
          border: "1px solid var(--c-border)",
        }}>
          <thead>
            <tr style={{ background: "var(--c-surface-2,var(--c-surface))" }}>
              {["WO ID", "タイトル", "種別", "ステータス"].map(h => (
                <th key={h} style={{
                  ...cell, fontWeight: 600, fontSize: 11,
                  color: "var(--c-text-3)", textAlign: "left",
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayed.map(w => {
              const color = WO_STATUS_COLOR[w.work_order_status] || "#999";
              return (
                <tr key={w.work_order_id}>
                  <td style={{ ...cell, fontFamily: "var(--font-mono, monospace)",
                               fontSize: 12, color: "var(--c-text-3)" }}>
                    {w.work_order_id ? w.work_order_id.slice(0, 8) + "…" : "—"}
                  </td>
                  <td style={{ ...cell, fontWeight: 500 }}>
                    {w.title || "(無題)"}
                  </td>
                  <td style={{ ...cell, color: "var(--c-text-2)", fontSize: 12 }}>
                    {w.work_order_type || "—"}
                  </td>
                  <td style={cell}>
                    <span style={{
                      display: "inline-block",
                      background: color + "18",
                      color,
                      borderRadius: 4, padding: "2px 8px",
                      fontSize: 11.5, fontWeight: 600,
                    }}>
                      {WO_STATUS_LABEL[w.work_order_status] || w.work_order_status || "—"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

window.SchedulePage = SchedulePage;
