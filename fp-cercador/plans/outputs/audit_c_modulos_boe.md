# Auditoria pla 078 — mòduls dels C LOMLOE contra el BOE

Generat per `scripts/audit_c_modulos_boe.py` a partir de `c_modulos.json`/`bc_lomloe.json`
de producció i dels decrets: RD 207/2025 ([BOE-A-2025-6797](https://www.boe.es/buscar/act.php?id=BOE-A-2025-6797)), RD 208/2025 ([BOE-A-2025-7040](https://www.boe.es/buscar/act.php?id=BOE-A-2025-7040)), RD 209/2025 ([BOE-A-2025-6699](https://www.boe.es/buscar/act.php?id=BOE-A-2025-6699)), RD 210/2025 ([BOE-A-2025-7588](https://www.boe.es/buscar/act.php?id=BOE-A-2025-7588)), RD 211/2025 ([BOE-A-2025-7096](https://www.boe.es/buscar/act.php?id=BOE-A-2025-7096)), RD 212/2025 ([BOE-A-2025-7193](https://www.boe.es/buscar/act.php?id=BOE-A-2025-7193)), RD 213/2025 ([BOE-A-2025-7295](https://www.boe.es/buscar/act.php?id=BOE-A-2025-7295)), RD 86/2026 ([BOE-A-2026-3210](https://www.boe.es/buscar/act.php?id=BOE-A-2026-3210)).

- **OK**: els Graus B del catàleg són exactament l'oferta de Grau B del decret (annex II).
- **Forat del catàleg**: el decret ofereix un Grau B que el catàleg no té.
- **Catàleg de més**: el catàleg té un Grau B que el decret no ofereix.
- SSC_C_017_5B (RD 86/2026) té una altra estructura i surt com a no parsejat: es va
  verificar a mà (annex I: només 1705, 1706, 1707, 1783, 1784, 1785 com a Grau B).

| Resultat | Certificats |
|---|---|
| OK | 331 |
| Forat del catàleg | 1 |
| Catàleg de més | 35 |
| Decret trobat, no parsejat | 1 |
| Sense decret localitzat | 32 |

Total: 400 certificats; 514 mòduls de fitxa sense Grau B al catàleg.

## Mòduls sense Grau B al catàleg (els que la UI mostrarà sense enllaç)

| Resultat | Mòduls | Nota a la UI |
|---|---|---|
| Cap decret l'ofereix com a Grau B | 467 | art. 58.3 RD 659/2023 |
| El decret l'ofereix com a Grau B i el catàleg no el té | 1 | neutra |
| Només existeix com a Grau B d'una altra família | 13 | a decidir |
| Cap decret l'ofereix, però el decret del C no s'ha localitzat | 33 | a decidir |
| **Total** | **514** | |

### Forats del catàleg (per mòdul)

| C | Mòdul | Nom | B existents |
|---|---|---|---|
| HOT_C_003_5B | 0178 | Comercialización de eventos |  |

### Grau B d'una altra família

| C | Mòdul | Nom | B existents |
|---|---|---|---|
| AFD_C_003_4B | 0020 | Primeros auxilios | HOT_B_0020, SSC_B_0020 |
| AGA_C_006_5B | 0790 | Técnicas de educación ambiental | SEA_B_0790 |
| COM_C_003_4B | 0156 | Inglés profesional | ADG_B_0156, HOT_B_0156, MAP_B_0156, TMV_B_0156 |
| COM_C_006_4B | 0156 | Inglés profesional | ADG_B_0156, HOT_B_0156, MAP_B_0156, TMV_B_0156 |
| FME_C_002_5B | 0165 | Gestión de la calidad, prevención de riesgos laborales y protección ambiental | TCP_B_0165, VIC_B_0165 |
| FME_C_004_5B | 0165 | Gestión de la calidad, prevención de riesgos laborales y protección ambiental | TCP_B_0165, VIC_B_0165 |
| MAM_C_002_4B | 0538 | Materiales en carpintería y mueble | TMV_B_0538 |
| MAM_C_005_4B | 0538 | Materiales en carpintería y mueble | TMV_B_0538 |
| MAM_C_006_4B | 0538 | Materiales en carpintería y mueble | TMV_B_0538 |
| SEA_C_001_5B | 0017 | Habilidades sociales | SSC_B_0017 |
| SSC_C_003_5B | 0179 | Inglés profesional | ADG_B_0179, ARG_B_0179, COM_B_0179, HOT_B_0179, MAP_B_0179 |
| SSC_C_004_5B | 0179 | Inglés profesional | ADG_B_0179, ARG_B_0179, COM_B_0179, HOT_B_0179, MAP_B_0179 |
| VIC_C_002_4B | 0116 | Principios de mantenimiento electromecánico | QUI_B_0116, TCP_B_0116 |

### Mòduls de C sense decret localitzat

| C | Mòdul | Nom | B existents |
|---|---|---|---|
| AGA_C_010_4B | 1782 | Prevención de riesgos laborales |  |
| AGA_C_010_5B | 1782 | Prevención de riesgos laborales |  |
| AGA_C_011_4B | 1782 | Prevención de riesgos laborales |  |
| ARG_C_008_5B | 1800 | Gestión y actualización de la documentación técnica |  |
| ARG_C_008_5B | 1782 | Prevención de riesgos laborales |  |
| ART_C_001_5B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| ART_C_002_5B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| ART_C_003_5B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| ENA_C_003_4B | 1724 | Prevención de riesgos laborales en construcción |  |
| ENA_C_009_5B | 1782 | Prevención de riesgos laborales |  |
| EOC_C_009_4B | 1724 | Prevención de riesgos laborales en construcción |  |
| EOC_C_010_4B | 1724 | Prevención de riesgos laborales en construcción |  |
| EOC_C_011_4B | 1724 | Prevención de riesgos laborales en construcción |  |
| EOC_C_012_4B | 1724 | Prevención de riesgos laborales en construcción |  |
| HOT_C_015_5B | 1782 | Prevención de riesgos laborales |  |
| HOT_C_016_5B | 1782 | Prevención de riesgos laborales |  |
| IMA_C_007_4B | 1782 | Prevención de riesgos laborales |  |
| IMA_C_008_4B | 1782 | Prevención de riesgos laborales |  |
| IMA_C_009_4B | 1724 | Prevención de riesgos laborales en construcción |  |
| IMA_C_010_4B | 1724 | Prevención de riesgos laborales en construcción |  |
| IMP_C_006_4B | 1782 | Prevención de riesgos laborales |  |
| IMP_C_012_5B | 1782 | Prevención de riesgos laborales |  |
| MAM_C_007_4B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| QUI_C_006_4B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| SEA_C_001_4B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| SEA_C_002_4B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| SEA_C_003_4B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| SEA_C_004_4B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| SEA_C_005_4B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| SEA_C_006_4B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| SSC_C_001_4B | 1782 | Prevención de riesgos laborales |  |
| SSC_C_002_4B | 1732 | Nivel básico en prevención de riesgos profesionales |  |
| TCP_C_008_4B | 1782 | Prevención de riesgos laborales |  |

### Mòduls que cap decret ofereix com a Grau B

0036 Máquinas y equipos térmicos, 0134 Configuración de instalaciones térmicas y de fluidos, 0155 Técnicas de comunicación en restauración, 0166 Verificación de productos, 0224 Sistemas operativos en red, 0228 Aplicaciones web, 0264 Moda y tendencias, 0266 Configuración de instalaciones caloríficas, 0277 Técnicas en confección, 0279 Muestras de artículos en textil y piel, 0309 Técnicas de comunicación y de relaciones, 0360 Equipos microinformáticos, 0370 Planificación y administración de redes, 0373 Lenguajes de marcas y sistemas de gestión de información, 0383 Destinos turísticos, 0385 Servicios de información turística, 0413 Comercialización de productos agroecológicos, 0432 Técnicas de fabricación mecánica, 0470 Innovación alimentaria, 0502 Gastronomía y nutrición, 0520 Sistemas y circuitos eléctricos, 0533 Verificación de productos conformados, 0551 Elementos de sistemas de telecomunicaciones, 0555 Redes telemáticas, 0557 Sistemas integrados y hogar digital, 0562 Estructuras de construcción, 0611 Calzado y tendencias, 0639 Actividades en cabina de estética, 0640 Imagen corporal y hábitos saludables, 0642 Perfumería y cosmética natural, 0661 Protocolo empresarial, 0663 Gestión avanzada de la información, 0690 Botánica agronómica, 0788 Gestión ambiental, 0789 Métodos y productos cartográficos, 0827 Comercio digital internacional, 0836 Prevención de incendios forestales, 0838 Uso público en espacios naturales, 0848 Peluquería y estilismo masculino, 0871 Identificación de materiales en preimpresión, 0872 Ensamblado de publicaciones electrónicas, 0883 Impresión en bajorrelieve, 0895 Tecnologías de mecanizado en piedra natural, 0931 Marketing digital, 0938 Elementos de máquinas, 0940 Representación gráfica de sistemas mecatrónicos, 0964 Informática industrial, 1019 Instalaciones, innovación y sistemas de automatización en acuicultura, 1034 Instalaciones y servicios, 1059 Infraestructuras y desarrollo del mantenimiento electrónico, 1070 Estudio de la imagen, 1072 Peluquería en cuidados especiales, 1081 Operación y manejo de maquinaria de excavación, 1118 Técnicas de intervención comunicativa, 1181 Asesoría cosmética, 1189 Imagen corporativa, 1218 Materiales para postimpresión, 1235 Comercio electrónico, 1248 Inmersión desde campana húmeda, 1267 Diseño digital de personajes 2d 3d, 1269 Productos de caracterización y maquillaje, 1282 Gestión de centros veterinarios, 1314 Organización de la guardia de máquinas, 1338 Guía en el medio natural acuático, 1339 Maniobras con cuerdas, 1406 Intervención socioeducativa para la igualdad, 1480 Comercialización de productos gráficos y atención al cliente, 1559 Replanteo en redes de agua, 1614 Ofimática aplicada al comercio alimentario, 1615 Gestión de un comercio alimentario, 1618 Preparación de embarcaciones de recreo para trabajos de mantenimiento, 1653 Técnicas de conducción, 1656 Educación vial, 1659 Movilidad segura y sostenible, 1724 Prevención de riesgos laborales en construcción, 1782 Prevención de riesgos laborales, 1786 Competencia digital para la práctica docente, 3007 Procesos básicos de panadería, 3026 Dispensación en panadería y pastelería, 3111 Envasado y distribución de materias primas agroalimentarias, 3145 Actividades de apoyo a personas no dependientes en la unidad convivencial, 3146 Seguridad en el ámbito doméstico

## Forats del catàleg

| C | Decret | B al BOE | B al catàleg |
|---|---|---|---|
| HOT_C_003_5B | RD 213/2025 | 0171, 0172, 0173, 0178, 0179 | 0171, 0172, 0173, 0179 |

## Catàleg de més

| C | Decret | B al BOE | B al catàleg |
|---|---|---|---|
| AGA_C_005_5B | RD 207/2025 | 0811 | 0692, 0811 |
| AGA_C_007_4B | RD 207/2025 | 0835 | 0404, 0835 |
| COM_C_003_5B | RD 212/2025 | 0623, 1109, 1110 | 0179, 0623, 1109, 1110 |
| ENA_C_006_5B | RD 210/2025 | 0681 | 0681, 0682 |
| HOT_C_005_5B | RD 213/2025 | 0172, 0179, 0180, 0397 | 0171, 0172, 0179, 0180, 0397 |
| HOT_C_006_4B | RD 213/2025 | 0031, 0156 | 0031, 0150, 0152, 0156 |
| HOT_C_007_5B | RD 213/2025 | 0179, 0384, 0386 | 0179, 0180, 0384, 0386 |
| IFC_C_007_5B | RD 207/2025 | 0612, 0614, 0615 | 0485, 0612, 0614, 0615 |
| IFC_C_008_5B | RD 207/2025 | 0483, 0484, 0613 | 0483, 0484, 0485, 0613 |
| IMA_C_003_5B | RD 209/2025 | 0124, 0133 | 0121, 0123, 0124, 0133 |
| IMP_C_001_3B | RD 209/2025 | 3005, 3060, 3065 | 3005, 3060, 3064, 3065 |
| IMP_C_002_3B | RD 209/2025 | 3005, 3061, 3063 | 3005, 3061, 3062, 3063 |
| MAP_C_004_4B | RD 212/2025 | 1032, 1033, 1172, 1177 | 0156, 1032, 1033, 1172, 1177 |
| MAP_C_005_4B | RD 212/2025 | 1032, 1033, 1173, 1174 | 0156, 1032, 1033, 1173, 1174 |
| MAP_C_006_4B | RD 212/2025 | 1032, 1033, 1175, 1176 | 0156, 1032, 1033, 1175, 1176 |
| MAP_C_011_4B | RD 212/2025 | 1027, 1030, 1032, 1033, 1035, 1036 | 0156, 1027, 1030, 1032, 1033, 1035, 1036 |
| MAP_C_012_4B | RD 212/2025 | 1029, 1032, 1033 | 0156, 1029, 1032, 1033 |
| MAP_C_013_4B | RD 212/2025 | 1028, 1032, 1033 | 0156, 1028, 1032, 1033 |
| SSC_C_002_5B | RD 208/2025 | 0013, 0014, 0017 | 0013, 0014, 0017, 0020 |
| SSC_C_003_5B | RD 208/2025 | 1124, 1126 | 0020, 1124, 1126 |
| SSC_C_005_5B | RD 208/2025 | 0337, 0339, 0340, 0343, 0344 | 0017, 0020, 0337, 0339, 0340, 0343, 0344 |
| SSC_C_006_5B | RD 208/2025 | 0337, 0342, 0343, 0344 | 0017, 0337, 0342, 0343, 0344 |
| SSC_C_008_5B | RD 208/2025 | 0341, 0342, 0343 | 0017, 0341, 0342, 0343 |
| SSC_C_010_5B | RD 208/2025 | 0344, 1402 | 0017, 0020, 0344, 1402 |
| SSC_C_011_5B | RD 208/2025 | 1115, 1116 | 1111, 1112, 1115, 1116 |
| TCP_C_003_4B | RD 211/2025 | 0269, 0604, 0605, 0606, 0607 | 0116, 0269, 0604, 0605, 0606, 0607 |
| TCP_C_006_4B | RD 211/2025 | 1041, 1044, 1046, 1047 | 0116, 1041, 1044, 1046, 1047 |
| TCP_C_007_4B | RD 211/2025 | 1041, 1044, 1045 | 0116, 1041, 1044, 1045 |
| TMV_C_003_4B | RD 211/2025 | 0452, 0453 | 0260, 0452, 0453 |
| TMV_C_004_4B | RD 211/2025 | 0456, 0457, 0458 | 0260, 0456, 0457, 0458 |
| TMV_C_005_4B | RD 211/2025 | 0454, 0455 | 0260, 0454, 0455 |
| TMV_C_006_4B | RD 211/2025 | 0452, 0456, 0718, 0742 | 0260, 0452, 0456, 0718, 0742 |
| TMV_C_007_4B | RD 211/2025 | 0714, 0715, 0716, 0717 | 0260, 0714, 0715, 0716, 0717 |
| TMV_C_013_4B | RD 211/2025 | 0156, 1175, 1623 | 0156, 0260, 1175, 1623 |
| TMV_C_014_4B | RD 211/2025 | 0156, 1619, 1620 | 0156, 0260, 1619, 1620 |

## Decret trobat però no parsejat

| C | Decret | B al BOE | B al catàleg |
|---|---|---|---|
| SSC_C_017_5B | RD 86/2026 |  | 1705, 1706, 1707, 1783, 1784, 1785 |

## Fitxa todofp diferent de l'annex I del decret

| C | Fitxa | BOE annex I |
|---|---|---|
| COM_C_001_4B | 1782, 1229, 1235, 1228, 1227 | 1227, 1229, 1228, 1233, 1235, 1782 |
| COM_C_002_4B | 1782, 1235, 1231, 1232, 1230 | 1230, 1231, 1232, 1233, 1235, 1782 |
| COM_C_003_4B | 1782, 1235, 0156, 1234 | 0156, 1233, 1234, 1235, 1782 |
| COM_C_004_4B | 1606, 1613, 1615, 1782 | 1606, 1613, 1614, 1615, 1782 |
| IMA_C_001_4B | 0302, 0266, 0038, 1782, 0037 | 0037, 0038, 0302, 1782 |
| IMA_C_002_4B | 0392, 1782, 0393, 0036 | 0310, 0392, 0393, 0036, 0266, 1782 |
| IMA_C_006_5B | 0941, 0942, 1782, 0943, 0940 | 0940, 0941, 0942, 0944, 0943, 1782 |
| IMP_C_003_4B | 0635, 1782, 0639 | 0635, 0639, 0640, 1782 |
| IMP_C_009_5B | 1782, 1267, 1261, 0685 | 0685, 1261, 1267, 1268, 1782 |
| SSC_C_002_3B | 1782, 3102, 3145 | 3102, 3145, 3146, 1782 |
| SSC_C_012_5B | 1115, 1116, 1782, 1113, 1114, 1118 | 1113, 1114, 1115, 1116, 1117, 1118, 1782 |

## Sense decret localitzat (revisar a mà)

AGA_C_010_4B, AGA_C_010_5B, AGA_C_011_4B, ARG_C_008_5B, ART_C_001_5B, ART_C_002_5B, ART_C_003_5B, ENA_C_003_4B, ENA_C_009_5B, EOC_C_009_4B, EOC_C_010_4B, EOC_C_011_4B, EOC_C_012_4B, HOT_C_015_5B, HOT_C_016_5B, IMA_C_007_4B, IMA_C_008_4B, IMA_C_009_4B, IMA_C_010_4B, IMP_C_006_4B, IMP_C_012_5B, MAM_C_007_4B, QUI_C_006_4B, SEA_C_001_4B, SEA_C_002_4B, SEA_C_003_4B, SEA_C_004_4B, SEA_C_005_4B, SEA_C_006_4B, SSC_C_001_4B, SSC_C_002_4B, TCP_C_008_4B
