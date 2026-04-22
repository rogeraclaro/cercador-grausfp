Hi ha un tema nou: Al llistat hi ha tota una familia (certificados de profesionalidad) que provenen del pla antic. Doncs bé, certificados de profesionalidad NO es cap familia. Es el terme que amb el pla nou es correspon als graus C! A més tal i com esta ara, tota aquesta familia
té formacions amb graus A i B, pero cap amb grau C, o sigui que es totalment incongruent. Abans d'eliminar-los sense més, necessito controlar-ho bé, i per a aixo hauries d'investigar d'on han sortit aquestes formacions, com s'han incporporat, si estan repetides respecte de les
formacions de grau C i veure quin script d'escrapping s'ha de corregir/modificar. Fés tot aixo amb molta cura, revisa en profunditat i finalment exposa-m'ho per a que ho pugui comprendre i revisar. No facis cap canvi al codi!

⏺ Entenc el problema. Cal investigar a fons per què "Certificados de Profesionalidad" apareix com a família per als Graus A i B, quan en realitat és l'equivalent als Graus C del nou pla. També he de verificar si hi ha duplicacions amb els Graus C i identificar l'script de scraping
responsable. No faré cap canvi al codi.

Començaré buscant la cadena "Certificados de Profesionalidad" a tot el projecte per trobar on es defineix i s'utilitza.

Searched for 1 pattern (ctrl+o to expand)

⏺ El Grep ha trobat moltes coincidències, incloent el fitxer de dades fp-cercador/backend/data/ofertes.json i diversos fitxers de planificació.

La part important del resultat del grep és:

- .claude/worktrees/agent-ab134a7f/.planning/phases/02-pdf-scrapers-grados-a-b-c/02-03-SUMMARY.md:48:- UF → 'Certificados de Profesionalidad' (2.794 registres)
- .claude/worktrees/agent-ab134a7f/.planning/phases/02-pdf-scrapers-grados-a-b-c/02-03-SUMMARY.md:49:- MF → 'Certificados de Profesionalidad' (1.834 registres)
- fp-cercador/backend/scrapers/pdf_scraper.py:54: 'UF': 'Certificados de Profesionalidad',
- fp-cercador/backend/scrapers/pdf_scraper.py:55: 'MF': 'Certificados de Profesionalidad',

Això confirma que:

1. Els prefixes UF i MF s'estan mapant a la família "Certificados de Profesionalidad" a pdf_scraper.py.
2. Aquests prefixes corresponen a "Famílies del pla antic / LOGSE / HTML-only" segons els comentaris a pdf_scraper.py.
3. Aquests registres estan presents a fp-cercador/backend/data/ofertes.json.

Ara, necessito investigar més a fons pdf_scraper.py per entendre com es processen els codis UF i MF i com es determina el grado per a aquestes entrades, ja que menciones que tenen grado A i B quan haurien de ser grado C o equivalents.

També, buscaré a pdf_scraper.py com es determinen els graus A, B i C per comparar.

Començaré llegint pdf_scraper.py per examinar la definició de PREFIX_MAP i la lògica d'assignació de grado.

Read 1 file (ctrl+o to expand)

⏺ He revisat pdf_scraper.py en profunditat. Aquí teniu les meves conclusions:

1. Origen dels "Certificados de Profesionalidad" i com s'han incorporat:

- PREFIX_MAP (línies 25-58): Aquest diccionari defineix el mapeig dels prefixes de codi a les famílies professionals. Les línies 54 i 55 són les responsables:
  'UF': 'Certificados de Profesionalidad',
  'MF': 'Certificados de Profesionalidad',
- Els comentaris adjunts indiquen "Famílies del pla antic / LOGSE / HTML-only". Això vol dir que UF i MF són identificadors de codis de qualificacions del "pla antic" (probablement anteriors a la LOE 3/2022).
- \_extract_records (línies 166-229): Aquesta funció és el nucli de l'extracció de dades dels PDFs. A les línies 204-213, es dedica a extreure el prefix del codi (com UF, MF, AFD, FME, etc.) i buscar-lo a PREFIX_MAP per assignar la familia.
- Les funcions parse_grado_a, parse_grado_b, parse_grado_c (línies 257-269): Cadascuna d'aquestes funcions crida \_extract_records amb la grado_letter corresponent ('A', 'B', 'C'). Això significa que si un PDF de Grado A o B conté codis amb prefix UF o MF, se'ls assignarà la família
  "Certificados de Profesionalidad".

2. Per què apareixen amb Graus A i B (incongruència):

- La lògica d'assignació de grado (A, B, C) es fa a la funció pipeline.py (segons el docstring a la línia 13: "Camp 'id' i 'grado' els afegeix pipeline.py, NO aquest mòdul."). L'script pdf_scraper.py simplement extreu la familia, codigo, denominacion, nivel, etc. del PDF.
- Per tant, és pipeline.py qui, basant-se en alguna lògica (probablement el pdf_path que se li passa a parse_grado_a/b/c), assigna el grado final als registres.
- Si un PDF que està sent processat per parse_grado_a (i per tant se li assignarà grado: A a pipeline.py) conté línies amb codis UF o MF, aquests registres acabaran amb grado: A i familia: Certificados de Profesionalidad. El mateix passaria amb els Grados B.

3. Si estan repetides respecte de les formacions de Grau C:

- Aquesta part és més difícil de determinar sense una comparació directa amb les dades dels Graus C.
- Els "Certificados de Profesionalidad" són l'equivalent als Graus C del nou pla. És possible que hi hagi una superposició de contingut entre les formacions antigues (UF/MF) i les noves (Grado C).
- La meva hipòtesi és que sí, que molts d'aquests certificats del pla antic seran equivalents o molt similars a formacions de Grau C actuals, però la base de dades els tracta com entitats separades a causa de la seva provinença i el mapeig de PREFIX_MAP.

4. Quin script d'escrapping s'ha de corregir/modificar:

- L'script que conté la definició problemàtica és fp-cercador/backend/scrapers/pdf_scraper.py (per la definició a PREFIX_MAP).
- No obstant això, la pipeline.py també és crucial, ja que és qui assigna el grado final. Per abordar completament la inconsistència, probablement s'haurien de coordinar els dos scripts.

Resum i propostes (sense fer canvis):

El problema rau en el mapeig explícit de UF i MF a la família "Certificados de Profesionalidad" dins de pdf_scraper.py, juntament amb la lògica de pipeline.py que assigna el grado segons el context del PDF processat. Això resulta en la incongruència de veure "Certificados de
Profesionalidad" en graus A i B.

Per corregir-ho, caldria:

1. Revisar pipeline.py: Entendre exactament com s'assigna el grado (A, B, C) a cada registre un cop s'han parsejat els PDFs.
2. Modificar pdf_scraper.py i/o pipeline.py:


    - Opció 1 (Simplificada): Si els "Certificados de Profesionalidad" del pla antic sempre s'han de considerar Grau C (o equivalent), es podria modificar la lògica a pipeline.py perquè, un cop detecti una familia: Certificados de Profesionalidad, forci el grado: C per a aquests

registres, independentment de si venien d'un PDF que originalment era per Grau A o B. - Opció 2 (Més precisa): Si la intenció és eliminar completament "Certificados de Profesionalidad" com a família separada i integrar-los directament com a Graus C, llavors caldria eliminar les entrades UF i MF de PREFIX_MAP a pdf_scraper.py. Això implicaria que aquests codis es
mapessin a "Família Desconeguda" (amb un warning), i hauríem de desenvolupar un scraper específic per als Graus C del nou pla que capturen aquesta informació correctament. La memòria del projecte ja menciona: "Fase futura: dades addicionals Grado C — El buscadorcertificados té BOE,
fitxa PDF, duració, centres i Europass per als Grados C (LOE). Scraping via POST." Això suggereix que hi ha una font de dades més rica per als Graus C que podria substituir aquests "Certificados de Profesionalidad" antics.

Abans de fer qualsevol canvi, seria crucial decidir si els "Certificados de Profesionalidad" del pla antic s'han de considerar sempre Grau C, o si hi ha alguna raó per mantenir-los segregats o mapar-los a altres graus en funció de la seva equivalència real. També s'hauria de
considerar la possible redundància amb les dades del Grau C actual.
