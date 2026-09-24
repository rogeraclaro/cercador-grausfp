---
status: complete
---
# Subpage-specific fixes (step 2)

perfil: section nav scrolls horizontally on mobile, 44px on touch. observatori: uPlot dates/labels localized with Intl (ca/es), new keys obs.chart.date/total, canvas colours read from tokens, axis spacing 110. `<main id="main">` on login/register/forgot/reset/politica-privacitat. politica: provisional badge no longer uppercase, amber tokens. Auth message colours (error/success) moved to tokens on 4 pages.

Verified at 390/1000/1280 in a real browser: tabs 44px and scrollable without page overflow, legend "Data"/"Fecha", ES date "19 de junio de 2026", main width unchanged (1280), no console errors.

Not changed: the detector's cramped-padding on .topbar is a false positive (fixed 52px flex-centred bar).
