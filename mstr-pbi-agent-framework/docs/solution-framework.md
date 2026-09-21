# Solution framework summary (delivery view)

This maps the AI/n8n factory to the migration strategy used in the accompanying deck.

## Problem (structural)

| MicroStrategy | Power BI / Fabric | Migration implication |
|---|---|---|
| Global metrics | Model-scoped DAX measures | Metric catalogue → measure templates |
| Snowflake logical model | Star / Direct Lake preferred | Model reshape, not report copy |
| Grid consolidations | Filter-context evaluation | Subtotal semantics must be proven |
| Prompts shape queries | Slicers filter context | UX + security behaviour change |
| Security filters | RLS DAX predicates | Mandatory human security gate |

## Solution stages (control loop)

1. **Discover** — inventory what exists  
2. **Assess** — what makes it hard  
3. **Classify** — migrate / consolidate / redesign / retire  
4. **Transform** — map model, DAX, visuals, security, UX  
5. **Validate** — data, metrics, behaviour, security, performance  
6. **Certify** — business sign-off + controlled release  

## Factory lanes

- **Automate** — metadata, standard mappings, repetitive DAX, docs/checks  
- **Review** — complex metrics, prompts, aggregation, security mappings  
- **Hand-build** — unique logic, complex models, UX redesign  

Quality gate: no release until semantics + security + behaviour reconcile.

## Automation stance

**Hybrid accelerator:** commercial converters (if licensed) for coverage baselines + this **internal n8n agent factory** for decisioning, mapping catalogue, validation plans, and evidence. Humans retain judgement on security and business-critical outputs.

## Sample translations (A/B/C)

See `samples/*/expected-blueprint.json` for concrete Power BI blueprints produced by the Transform patterns.
