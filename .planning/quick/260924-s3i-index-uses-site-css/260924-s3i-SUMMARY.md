---
status: complete
---
# index.html uses site.css (step 3)

Removed from index.html the :root block and 21 rules identical to site.css (base + 768px media); linked `site.css?v=1`. Verified pixel-identical: 12 screenshots (1280/390/320, logged in/out, before and after a search) have equal md5 vs the pre-change baseline; no console errors.

All 14 pages now share tokens and masthead from `frontend/site.css`. Bump `?v=` in every page when site.css changes.
