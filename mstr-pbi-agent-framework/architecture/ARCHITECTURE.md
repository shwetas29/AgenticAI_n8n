# Architecture — MSTR → PBI Agent Factory (n8n)

## 1. Control loop

Every report object (report, dossier, document) follows one path:

```
┌──────────┐   ┌────────┐   ┌──────────┐   ┌────────────┐   ┌──────────┐   ┌──────────┐
│ Discover │ → │ Assess │ → │ Classify │ → │ Transform  │ → │ Validate │ → │ Certify  │
└──────────┘   └────────┘   └──────────┘   └────────────┘   └──────────┘   └──────────┘
      │              │             │               │               │              │
      └──────────────┴────── Evidence / Decision Log ──────────────┴──────────────┘
```

Disposition after Classify:

- **MIGRATE** — high automation, standard patterns
- **CONSOLIDATE** — merge into an existing semantic model / report family
- **REDESIGN** — rebuild UX/model; agents draft, humans own
- **RETIRE** — stop; archive inventory + rationale

## 2. Execution lanes

```
                 ┌──────────── Automate ────────────┐
  Report pack →  │  inventory, mappings, DAX templates, checks │
                 └─────────────────┬────────────────┘
                                   │ complexity / risk score
                 ┌─────────────────▼────────────────┐
                 │            Review queue           │
                 │  metrics · prompts · security     │
                 └─────────────────┬────────────────┘
                                   │ exceptions
                 ┌─────────────────▼────────────────┐
                 │           Hand-build              │
                 │  unique logic · UX · model design │
                 └─────────────────┬────────────────┘
                                   │
                          ┌────────▼────────┐
                          │  Quality gate   │
                          └─────────────────┘
```

Human-in-the-loop is a **control**, not a bottleneck: only items above policy thresholds pause.

## 3. n8n topology

```
[Webhook / Manual / Queue]
          │
          ▼
   00-orchestrator  ──────────────────────────────────────────┐
          │                                                   │
          ├──► 01-discovery (sub-workflow)                    │
          ├──► 02-assessor                                    │
          ├──► 03-classifier                                  │
          ├──► 04-transformer                                 │
          ├──► 05-validator                                   │
          ├──► 06-certifier                                   │
          │                                                   │
          ├──► HITL wait (n8n Wait / Form / Slack approve)    │
          └──► Evidence sink (Data table / Postgres / Sheet) ─┘
```

Specialist workflows are invoked with **Execute Workflow** so they stay independently testable and reusable across programmes.

## 4. Component map

| Component | Responsibility | Talks to |
|---|---|---|
| Orchestrator | State machine, retries, lane routing | All agents, evidence store |
| Discovery agent | Parse intake + optional MSTR REST metadata | MSTR API / intake JSON |
| Assessor agent | Score complexity & risk dimensions | Pattern catalogue |
| Classifier agent | Disposition + consolidation candidates | Classification policy |
| Transformer agent | Emit PBI blueprint (model, DAX, visuals, RLS) | Mapping catalogue + LLM |
| Validator agent | Checklist + reconciliation plan | Validation policy |
| Certifier agent | Sign-off pack + release notes | Evidence store |
| Evidence / decision layer | Mapping catalogue rows, decision log, validation results | Postgres / Sheets / Data store |
| Mapping catalogue | Deterministic MSTR→PBI patterns | Assessor, Transformer |

## 5. AI vs deterministic split

| Concern | Owner | Why |
|---|---|---|
| Metric → DAX template selection | Rules engine + catalogue | Repeatable, auditable |
| Ambiguous metric intent | LLM + Review lane | Needs judgement |
| Visual type suggestion | LLM constrained by catalogue | Soft mapping |
| RLS predicate draft | LLM + mandatory Review | Security-critical |
| Disposition scoring | Deterministic policy | Consistent across estate |
| Narrative docs / release notes | LLM | Cheap to automate |

## 6. Target evidence artefacts

Per report GUID:

1. `inventory.json` — Discovery
2. `assessment.json` — Assessor
3. `classification.json` — Classifier
4. `pbi-blueprint.json` — Transformer
5. `validation-plan.json` — Validator
6. `certification-pack.json` — Certifier
7. `decision-log.jsonl` — append-only events

These contracts live under `../schemas/` so any n8n node, script, or external tool can exchange the same shapes.

## 7. Deployment sketch (n8n)

- **n8n Cloud** or self-hosted (Docker) with Postgres for execution data.
- Credentials: LLM provider, optional MSTR REST, optional Fabric REST / SPN.
- Shared Data Store / Postgres table `migration_evidence`.
- Queue trigger (optional) for wave-based batching (100s of reports).

## 8. Reuse across clients

Keep **agents + schemas + prompts** stable. Swap:

- `mappings/pattern-catalogue.json` (client patterns)
- `config/classification-policy.json` (thresholds)
- `samples/` (estate packs)
- Branding / Slack channels in HITL nodes
