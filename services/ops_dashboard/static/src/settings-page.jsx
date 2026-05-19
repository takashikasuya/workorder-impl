/* settings-page.jsx — ダッシュボード設定 (nav=settings) */

function SettingsSection({ title, children }) {
  return (
    <div style={{
      background: "var(--c-surface)", border: "1px solid var(--c-border)",
      borderRadius: 10, padding: "20px 24px", marginBottom: 16,
    }}>
      <div style={{
        fontSize: 11, fontWeight: 600, color: "var(--c-text-3)",
        textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 14,
      }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function SettingsRow({ label, hint, children }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "10px 0", borderBottom: "1px solid var(--c-border)",
    }}>
      <div>
        <span style={{ fontSize: 13, color: "var(--c-text)" }}>{label}</span>
        {hint && <div style={{ fontSize: 11, color: "var(--c-text-3)", marginTop: 2 }}>{hint}</div>}
      </div>
      <div style={{ display: "flex", gap: 6 }}>{children}</div>
    </div>
  );
}

function SettingsRadioBtn({ value, current, onClick, label }) {
  const active = current === value;
  return (
    <button onClick={onClick} style={{
      padding: "5px 14px", fontSize: 12, borderRadius: 6, cursor: "pointer",
      background: active ? "var(--c-primary)" : "var(--c-surface-2,var(--c-surface))",
      color: active ? "#fff" : "var(--c-text-2)",
      border: `1px solid ${active ? "var(--c-primary)" : "var(--c-border)"}`,
      fontWeight: active ? 600 : 400,
      transition: "all var(--t-fast, 120ms)",
    }}>
      {label}
    </button>
  );
}

function SettingsPage({ theme, setTheme, t, setTweak }) {
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "0 24px 48px" }}>
      <div className="page-header" style={{ paddingTop: 0 }}>
        <div className="page-title">
          <h1>ダッシュボード設定</h1>
          <p>表示・テーマ・レイアウトの設定。変更はセッションをまたいで保持されます。</p>
        </div>
      </div>

      <SettingsSection title="表示">
        <SettingsRow label="テーマ" hint="ライト / ダーク モードを切り替えます">
          <SettingsRadioBtn value="light" current={t.theme || "light"} label="Light"
                    onClick={() => { setTweak("theme", "light"); setTheme("light"); }} />
          <SettingsRadioBtn value="dark"  current={t.theme || "light"} label="Dark"
                    onClick={() => { setTweak("theme", "dark");  setTheme("dark");  }} />
        </SettingsRow>
        <SettingsRow label="密度" hint="行の高さとスペーシングを調整します">
          <SettingsRadioBtn value="comfortable" current={t.density || "comfortable"} label="Comfortable"
                    onClick={() => setTweak("density", "comfortable")} />
          <SettingsRadioBtn value="compact"     current={t.density || "comfortable"} label="Compact"
                    onClick={() => setTweak("density", "compact")} />
        </SettingsRow>
      </SettingsSection>

      <SettingsSection title="主ビュー">
        <SettingsRow label="FlowRow 構成" hint="業務フロー一覧の表示レイアウト">
          <SettingsRadioBtn value="chain"  current={t.primary_view || "chain"}  label="Chain"
                    onClick={() => setTweak("primary_view", "chain")} />
          <SettingsRadioBtn value="kanban" current={t.primary_view || "chain"} label="Kanban"
                    onClick={() => setTweak("primary_view", "kanban")} />
        </SettingsRow>
      </SettingsSection>

      <SettingsSection title="バージョン情報">
        <div style={{ fontSize: 12, color: "var(--c-text-3)", lineHeight: 2 }}>
          <div><span style={{ fontWeight: 600, color: "var(--c-text-2)" }}>CS-OPS-DASHBOARD</span> v0.3.0</div>
          <div>IF-OPS-001 — 集約 BFF (FastAPI)</div>
          <div>React 18 + Babel Standalone (ビルドレス)</div>
        </div>
      </SettingsSection>
    </div>
  );
}

window.SettingsPage = SettingsPage;
