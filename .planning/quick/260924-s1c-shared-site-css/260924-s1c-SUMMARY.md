---
status: complete
---
# Shared site.css (step 1 of subpage review)

Extracted tokens (:root incl. --warm #755f51 and --fs-* scale) and masthead/lang-selector chrome (with mobile and coarse-pointer rules from index) into `frontend/site.css`, linked as `site.css?v=1` before each page's own `<style>` on 13 subpages. A script removed only rules identical to the shared ones (942 lines); differing ones stayed as overrides (`.lang-selector` margin-left:auto on the 5 auth pages). Bump `?v=` when site.css changes (static hosting, no build).

Verified at 390/320/1280 on 12 pages: masthead fits, no overlap, 44px touch buttons, --warm #755f51, no console errors. admin.html could not be exercised (redirects non-admins) but has the same link and rules.

Pending: step 2 (perfil tabs, observatori chart labels in English, <main> on 5 pages, uppercase body on politica-privacitat); step 3 (index.html to use site.css) + redeploy.
