# Extension guide — keep the framework reusable

## Do / don't

| Do | Don't |
|---|---|
| Add patterns to `mappings/pattern-catalogue.json` | Hard-code client rules into prompts |
| Tune `config/classification-policy.json` | Fork specialist agents per client |
| Drop new packs under `samples/` using intake schema | Change JSON schemas without versioning |
| Version catalogue (`version` field) | Bypass security HITL for “speed” |

## Add a pattern

```json
{
  "id": "PAT-CUSTOM-XYZ",
  "mstr": "...",
  "pbi": "...",
  "automation": "medium",
  "requiresReview": false,
  "daxTemplate": "..."
}
```

Then teach Assessor/Transformer via catalogue injection (pass catalogue JSON in the user prompt context from orchestrator).

## Add a new specialist

1. Create `prompts/07-your-agent.md`
2. Clone an `0x-*.json` workflow; change stage path + prompt
3. Wire Execute Workflow into orchestrator at the right control-loop step
4. Add/extend a schema under `schemas/`

## Connect real MicroStrategy

Add a pre-step before Discovery:

1. Auth to MSTR REST (`POST /api/auth/login`)
2. Fetch object definition / dossier definition
3. Map to `report-intake.schema.json`
4. Hand off to orchestrator

Keep the REST adapter **outside** specialist agents so agents stay estate-agnostic.

## Connect Fabric / Power BI

Post-Transformer automation ideas (separate n8n workflow):

- Create/update semantic model via Fabric APIs / TMDL repo commit
- Open PR with DAX + RLS stubs for human review
- Never auto-publish RLS changes without Certify

## Versioning

- Framework semver in `FRAMEWORK_VERSION`
- Catalogue `version`
- Schema `$id` paths stay stable; add fields as optional first
