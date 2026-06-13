<!-- GSD:project-start source:PROJECT.md -->
## Project

**Cercador FP España**

Aplicació web per cercar l'oferta formativa completa del Sistema de Formació Professional espanyol (Llei Orgànica 3/2022), cobrint els Grados A, B, C, D i E. Consta d'un backend Flask (Python) que extreu dades de PDFs oficials i scraping HTML del ministeri, i un frontend estàtic (HTML/CSS/JS vanilla) amb cerca en temps real. Es desplegarà en un VPS amb CloudPanel (Ubuntu 24.04).

**Core Value:** Un únic cercador que consolida tota l'oferta FP espanyola (Grados A–E) en temps real, filtrable per grado, família professional, nivell i text lliure.

### Constraints

- **Tech Stack**: Flask + HTML/CSS/JS vanilla — sense frameworks frontend; requisit explícit del propietari. Excepció acceptada: Alpine.js 3.x (vendoritzat a `frontend/vendor/`, sense CDN) per a la reactivitat d'`index.html`. No afegir-ne cap altre.
- **Dependencies**: pdfplumber, requests, beautifulsoup4, flask-cors, python-dotenv — cap altra
- **PDFs**: requereixen headers `Referer` i `User-Agent` per descarregar des de todofp.es
- **Rendiment**: el cercador ha de ser fluid fins a 1.500 registres sense paginació
- **Seguretat**: ADMIN_TOKEN NO al repositori; .env a .gitignore
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
