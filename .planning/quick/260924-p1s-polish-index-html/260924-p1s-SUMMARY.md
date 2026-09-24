---
status: complete
---
# Polish index.html

Done inline (no subagents). Mobile cards use flex gap instead of leading middle dots; FPO filters fit 320/390 (class filter-bar--fpo); grade tabs, pagination and FPO search reach 44px on coarse pointers; emoji bell/phone replaced by inline SVG; DESIGN.md gets the icon and separator rules. Verified in a real browser at 320/390/1280: no overflow, no text < 11px, no console errors or warnings.

Left out on purpose: no prefers-reduced-motion rules (motion is 150ms fades and a spinner; a global kill would hide loading feedback).
