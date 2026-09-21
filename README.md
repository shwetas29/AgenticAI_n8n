# MicroStrategy → Power BI migration assets

This repository contains:

1. **Strategy deck** — `MSTR_to_PowerBI_Migration_Strategy - Copy.pptx`
2. **Task brief** — `Report_Migration_Task_Details.pdf`
3. **Reusable AI agent framework (n8n)** — [`mstr-pbi-agent-framework/`](./mstr-pbi-agent-framework/)

## Framework at a glance

An n8n multi-agent factory that runs every report through:

`Discover → Assess → Classify → Transform → Validate → Certify`

with Automate / Review / Hand-build lanes, HITL gates for security-critical items, and an evidence bundle per report.

Start here: [`mstr-pbi-agent-framework/README.md`](./mstr-pbi-agent-framework/README.md)
