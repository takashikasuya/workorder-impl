# workorder-impl

建物FM ワークオーダー管理 SoS の **実装モノレポ**。
アーキテクチャ定義: [`workorder-systems`](../workorder-systems)
オントロジー: [`workorder-ontologies`](../workorder-ontologies)

---

## 構成

```
workorder-impl/
├── shared/                      # gutp-shared パッケージ
│   └── gutp/
│       ├── schemas/             # OWL → Pydantic v2 スキーマ（最重要）
│       │   ├── observation.py   # IoTEvent, Report
│       │   ├── issue.py         # Issue, StandardIssue, NonStandardIssue
│       │   ├── ticket.py        # Ticket, Estimate
│       │   ├── workorder.py     # WorkOrder, ServiceTask, Booking
│       │   └── payment.py       # Payment
│       ├── events/
│       │   └── subjects.py      # NATS サブジェクト定数
│       └── connectors/
│           ├── base.py          # Connector Protocol / ConnectorRegistry
│           └── rest/
│               └── router.py   # REST コネクタ（ビルOS → Webhook）
└── services/                   # 10 CS（workorder-systems の systems.yaml と一致）
    ├── obs_collector/           # CS-OBS-COLLECTOR     :8001  SOI-OBS
    ├── obs_analyzer/            # CS-OBS-ANALYZER      (worker) SOI-OBS
    ├── building_registry/       # CS-BUILDING-REGISTRY :8000  SOI-OBS
    ├── issue_manager/           # CS-ISSUE-MANAGER     :8002  SOI-WOM
    ├── ticket_manager/          # CS-TICKET-MANAGER    :8003  SOI-WOM
    ├── wo_manager/              # CS-WO-MANAGER        :8004  SOI-WOM
    ├── payment_manager/         # CS-PAYMENT-MANAGER   :8005  SOI-WOM
    ├── ops_dashboard/           # CS-OPS-DASHBOARD     :8006  SOI-WOM (BFF, PR #6)
    ├── notify_dispatcher/       # CS-NOTIFY-DISPATCHER (worker) SOI-WOM (ADR-003)
    └── wo_scheduler/            # CS-WO-SCHEDULER      (batch) SOI-WOM (ADR-004)
```

> **アーキ同期メモ**: 本リポジトリは雛形段階。`workorder-systems` の
> 確定アーキ（10CS / ADR-001〜004）に対し、以下の挙動は **未実装**:
> Report評価→Issue非同期（obs.report.evaluated）/ Issue pending_review・review /
> Booking conflicted / 緊急WO即時発行(FUN-WO-007) / 未評価Reportエスカレーション(FUN-OBS-007) /
> WO InProgress自動遷移 / ops_dashboard・notify_dispatcher のロジック。

---

## データフロー

```
ビルOS
  │  POST /ingest/iot-event  (REST コネクタ)
  │  POST /ingest/report
  ▼
obs-collector ──NATS: obs.iot-event.created──► obs-analyzer ──HTTP──► issue-manager
             └──NATS: obs.report.created────►                            │
                                                              NATS: issue.created
                                                                         │
                                                                    ticket-manager
                                                              NATS: ticket.estimate.approved
                                                                         │
                                                                    wo-manager
                                                                         │
                                                                 HTTP: /work-orders
                                                                    payment-manager
```

---

## コネクタ拡張

ビルOS 接続プロトコルを追加するには `shared/gutp/connectors/` に新ディレクトリを作成し、
`Connector` Protocol を実装して `obs_collector/main.py` の `lifespan` に登録するだけでよい。

```python
# services/obs_collector/gutp_obs_collector/main.py の lifespan 内
from gutp.connectors.grpc import GrpcConnector   # 新コネクタ
_registry.register(GrpcConnector(on_event=handle_ingress, port=50051))
```

現在実装済み:
- `rest/` — HTTP Webhook（`POST /ingest/iot-event`, `POST /ingest/report`）

追加候補:
- `grpc/` — gRPC ストリーミング
- `mqtt/` — MQTT ブリッジ（直接 IoT デバイス対応時）

---

## クイックスタート

```bash
# uv で依存解決
uv sync

# 全サービスを Docker Compose で起動
docker compose up -d

# ビルOS から IoTEvent を送信（REST コネクタ）
curl -X POST http://localhost:8001/ingest/iot-event \
  -H "Content-Type: application/json" \
  -d '{
    "iot_event_type": "gutp:SmokeAlarm",
    "event_state": "ACTIVE",
    "event_value": 98.5
  }'

# Issue 一覧を確認
curl http://localhost:8002/issues

# Ticket を起票
curl -X POST http://localhost:8003/tickets \
  -H "Content-Type: application/json" \
  -d '{"title": "煙感知器アラーム対応", "addresses_issue_ids": ["<issue_id>"]}'
```

---

## OWL スキーマ対応メモ

| Pydantic フィールド | OWL プロパティ | 備考 |
|---|---|---|
| `currency` | `gutp:currncy` | OWL タイポを正規化 |
| `task.work_order_id` | `gutp:isServiceTaskOf` | OWL の `isWorkOrderOf` 参照は typo |
| `task_id: str` | `gutp:taskID (xsd:dateTime)` | OWL 型宣言バグ → str |
| `payment.applies_to_work_order_id` | `gutp:appliesTo` | OWL range が rec:Agent は バグ → WorkOrder |
| `report_confidence: int` | `gutp:reportConfidence (xsd:string)` | コメント「確信度」より int が正 |
