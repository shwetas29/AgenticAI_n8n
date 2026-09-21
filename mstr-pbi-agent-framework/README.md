# MicroStrategy → Power BI AI Agent Framework (n8n)

Reusable multi-agent migration factory for converting MicroStrategy reports/dossiers into Power BI / Fabric artefacts. Built to run in **n8n**, with clear Automate / Review / Hand-build lanes and an auditable decision + evidence trail.

## Why this exists

MicroStrategy and Power BI are not 1:1. Global metrics, grid consolidations, prompts, and security filters do not map cleanly to DAX measures, filter context, slicers, and RLS. This framework standardises the **decision process** before the **build process**, so every report follows the same control loop:

```
Discover → Assess → Classify → Transform → Validate → Certify
```

## Design principles

| Principle | Meaning in this framework |
|---|---|
| Automate the repeatable | Deterministic mapping rules + LLM extraction for inventory, standard DAX patterns, docs |
| Review the business-critical | Human gates for complex metrics, security, aggregation intent |
| Hand-build the exceptional | Unique MSTR logic, UX redesign, ambiguous semantics |
| Evidence over opinion | Every stage writes to a decision log + mapping catalogue |
| Reusable across waves | Same agents, schemas, and prompts for any report estate |

## Package layout

```
mstr-pbi-agent-framework/
├── architecture/          # Control loop, agent topology, n8n deployment
├── n8n-workflows/         # Importable workflow JSON
├── schemas/               # JSON contracts between agents
├── prompts/               # System prompts per specialist agent
├── mappings/              # Pattern catalogue (MSTR → PBI)
├── samples/               # Sample A/B/C report packs
├── config/                # Env vars, credentials checklist
└── docs/                  # Ops guide, extension guide
```

## Quick start (n8n)

1. Import workflows from `n8n-workflows/` (order matters — see `docs/ops-guide.md`).
2. Create credentials: OpenAI (or Azure OpenAI), optional MicroStrategy REST, optional Power BI / Fabric.
3. Set environment variables from `config/env.example`.
4. Open **00-orchestrator** and run with a sample payload from `samples/`.
5. Review HITL items in the Review queue; approve to continue Transform → Validate → Certify.

## Agent roles

| Agent | Job | Typical lane |
|---|---|---|
| **Orchestrator** | Runs the control loop, routes by disposition | All |
| **Discovery** | Inventory report metadata, deps, usage signals | Automate |
| **Assessor** | Complexity, prompts, metrics, security risk | Automate + Review |
| **Classifier** | Migrate / Consolidate / Redesign / Retire | Automate + Review |
| **Transformer** | Produce PBI model, DAX, visuals, RLS sketch | Automate / Hand-build |
| **Validator** | Data, metrics, behaviour, security, perf checks | Automate + Review |
| **Certifier** | Package evidence for business sign-off | Review |

## Sample reports included

- **A – Regional Sales Performance**: crosstab → matrix + star schema + conditional format
- **B – Store Operations**: multi-page dossier → multi-page report with synced slicers + drill
- **C – Category Manager**: security filter + prompt + Top 10 → RLS + date slicer + TOPN

## Extending for a new estate

1. Add estate-specific rows to `mappings/pattern-catalogue.json`.
2. Drop new report packs under `samples/` using `schemas/report-intake.schema.json`.
3. Tune classifier thresholds in `config/classification-policy.json`.
4. Keep agent prompts stable; put client rules in mapping + policy files so the framework stays reusable.

## What this is / is not

**Is:** a reusable n8n agent factory with contracts, prompts, and migration patterns aligned to an Information Factory–style MSTR → PBI programme.

**Is not:** a fully automated pixel-perfect converter. Semantics, security, and UX still require human judgement at the quality gate.
