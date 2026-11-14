---
quick_id: 261114-ekq
date: 2026-11-14
---
# Audit fixes: verified low-risk defects from the full-project audit

Full read of backend, scrapers, scripts and frontend (four parallel read-only reviews plus
tests, pyflakes and repo hygiene). Scope of this task: fix only defects that were re-verified
in the code and are low-risk; everything else is listed in the SUMMARY for the owner.

Executed inline (no planner/executor subagents): the findings were already in context.

1. Backend robustness (alerts, unsubscribe tokens, centres refresh, observatory, SMTP).
2. Frontend error handling and state bugs (index.html, login, profile, admin, history).
3. Cache versions and status document.
