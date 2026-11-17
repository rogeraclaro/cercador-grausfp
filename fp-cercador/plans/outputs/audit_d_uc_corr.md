# Auditoria de `d_uc_corr.json` (pla 091)

Generat per `scripts/build_d_uc_corr.py`. Font: XML obert del BOE dels decrets que
enllaça la fitxa de cada cicle a todofp, més els decrets que en substitueixen annexos.

## Cobertura

| Tipus | Total | Amb taula A | Amb taula B | Taula vigent d'un decret posterior |
|---|---|---|---|---|
| Grau bàsic | 34 | 34 | 34 | 34 |
| Grau mitjà | 67 | 65 | 64 | 29 |
| Grau superior | 94 | 86 | 86 | 31 |

## Decrets que substitueixen o afegeixen taules

| Decret | Cicles | Títol |
|---|---|---|
| BOE-A-2024-10683 | 34 | Real Decreto 498/2024, de 21 de mayo, por el que se modifican determinados reales decretos por los que se establecen títulos de Formación Profesional  |
| BOE-A-2024-10684 | 27 | Real Decreto 499/2024, de 21 de mayo, por el que se modifican determinados reales decretos por los que se establecen títulos de Formación Profesional  |
| BOE-A-2024-10685 | 27 | Real Decreto 500/2024, de 21 de mayo, por el que se modifican determinados reales decretos por los que se establecen títulos de Formación Profesional  |
| BOE-A-2023-10396 | 3 | Real Decreto 290/2023, de 18 de abril, por el que se actualizan los títulos de la formación profesional del sistema educativo de Técnico en Operacione |
| BOE-A-2023-13219 | 1 | Real Decreto 403/2023, de 29 de mayo, por el que se actualiza el título de la formación profesional del sistema educativo de Técnico Superior en Gesti |
| BOE-A-2023-13220 | 1 | Real Decreto 404/2023, de 29 de mayo, por el que se actualizan los títulos de la formación profesional del sistema educativo de Técnico en Preimpresió |
| BOE-A-2023-13217 | 1 | Real Decreto 401/2023, de 29 de mayo, por el que se actualizan los títulos de la formación profesional del sistema educativo de Técnico Superior en Au |

57 cicles conserven a `convalida_anterior` la taula A original que un decret posterior va substituir: els certificats LOE porten els codis d'UC d'aquella taula.

3 cicles porten la taula llegida del PDF del BOE, perquè l'XML la publica com a imatge: `fabricacion-mecanica~mecanizado`, `industrias-alimentarias~panaderia-reposteria-confiteria`, `servicios-socioculturales-comunidad~educacion-infantil`.

## Cicles sense taula (10)

| Cicle | Nivell | Motiu | Decrets enllaçats |
|---|---|---|---|
| Técnico en Joyería (`fabricacion-mecanica~joyeria`) | 2 | the decree names no unit of competence | BOE-A-2003-10468, BOE-A-2003-16048 |
| Técnico Superior en Óptica de Anteojería (`fabricacion-mecanica~optica-anteojeria`) | 3 | the decree names no unit of competence | BOE-A-2001-8794, BOE-A-2003-6139 |
| Técnico Superior en Prevención de Riesgos Profesionales (Título LOGSE) (`mantenimiento-servicios-produccion~prevencion-riesgos-profesionales`) | 3 | the decree names no unit of competence | BOE-A-2021-18189, BOE-A-2001-21714, BOE-A-2003-6137 |
| Técnico en Cuidados Auxiliares de Enfermería (`sanidad~cuidados-auxiliares-enfermeria`) | 2 | the decree names no unit of competence | BOE-A-1995-13533, BOE-A-1995-13592 |
| Técnico Superior en Dietética (`sanidad~dietetica`) | 3 | the decree names no unit of competence | BOE-A-1995-13285, BOE-A-1995-13287 |
| Técnico Superior en Mantenimiento Aeromecánico de Aviones con Motor de Turbina (`transporte-mantenimiento-vehiculos~mtmo-aeromecanica-aviones-motor-turbina`) | 3 | the decree names no unit of competence | BOE-A-2022-10806, BOE-A-2019-545, BOE-A-2024-10685, BOE-A-2022-9846, BOE-A-2025-14430 |
| Técnico Superior en Mantenimiento Aeromecánico de Aviones con Motor de Pistón (`transporte-mantenimiento-vehiculos~mtmo-aeromecanico-aviones-motor-piston`) | 3 | the decree names no unit of competence | BOE-A-2019-544, BOE-A-2024-10685, BOE-A-2025-14430 |
| Técnico Superior en Mantenimiento Aeromecánico de Helicópteros con Motor de Pistón (`transporte-mantenimiento-vehiculos~mtmo-aeromecanico-helicopteros-motor-piston`) | 3 | the decree names no unit of competence | BOE-A-2019-546, BOE-A-2024-10685, BOE-A-2025-14430 |
| Técnico Superior en Mantenimiento Aeromecánico de Helicópteros con Motor de Turbina (`transporte-mantenimiento-vehiculos~mtmo-aeromecanico-helicopteros-motor-turbina`) | 3 | the decree names no unit of competence | BOE-A-2019-547, BOE-A-2024-10685, BOE-A-2025-14430 |
| Técnico Superior en Mantenimiento de Sistemas Electrónicos y Aviónicos de Aeronaves (`transporte-mantenimiento-vehiculos~mtmo-sistemas-electronicos-avionicos-aeronaves`) | 3 | the decree names no unit of competence | BOE-A-2019-548, BOE-A-2024-10685, BOE-A-2025-14430 |

## Files que no s'han pogut llegir (0)

Cap.

## UC de les taules A que no són cap mòdul B LOE del catàleg

311 de 1479 UC. La majoria són UC de qualificacions actualitzades (codis nous) que encara no tenen certificat al catàleg del pla antic.

ECP1690_2, ECP1853_3, ECP1854_3, ECP1855_3, ECP1856_3, ECP1857_3, ECP1862_3, ECP1863_3, ECP1864_3, ECP1865_3, ECP2519_2, UC0021_2, UC0022_2, UC0023_2, UC0024_2, UC0025_2, UC0064_3, UC0213_3, UC0214_3, UC0215_3, UC0252_3, UC0253_3, UC0254_3, UC0279_2, UC0280_2, UC0363_2, UC0364_2, UC0365_2, UC0366_2, UC0367_2, UC0368_2, UC0369_3, UC0370_3, UC0371_3, UC0372_3, UC0373_3, UC0374_3, UC0375_3, UC0376_3, UC0377_3, UC0378_3, UC0379_3, UC0380_3, UC0381_3, UC0382_3, UC0383_3, UC0384_3, UC0385_3, UC0386_3, UC0387_3, UC0388_3, UC0389_3, UC0390_3, UC0391_3, UC0392_3, UC0393_3, UC0394_3, UC0395_3, UC0396_3, UC0397_3, UC0398_3, UC0399_3, UC0400_3, UC0405_2, UC0406_2, UC0407_2, UC0408_3, UC0409_3, UC0410_3, UC0411_3, UC0412_3, UC0413_3, UC0448_2, UC0449_2, UC0450_2, UC0451_2, UC0452_2, UC0454_3, UC0455_3, UC0456_3, UC0457_3, UC0458_3, UC0459_3, UC0475_3, UC0476_3, UC0477_3, UC0478_3, UC0479_3, UC0480_3, UC0481_3, UC0626_3, UC0716_2, UC0723_2, UC0724_2, UC0747_3, UC0748_3, UC0749_3, UC0750_3, UC0751_3, UC0752_3, UC0753_3, UC0808_2, UC0892_2, UC0893_2, UC0903_3, UC0950_3, UC1027_3, UC1028_3, UC1029_3, UC1030_3, UC1031_3, UC1032_3, UC1033_3, UC1069_3, UC1070_3, UC1071_3, UC1072_3, UC1073_3, UC1091_3, UC1092_3, UC1093_3, UC1094_3, UC1139_2, UC1140_2, UC1141_2, UC1245_3, UC1246_3, UC1247_3, UC1402_2, UC1403_2, UC1404_2, UC1405_3, UC1406_3, UC1407_3, UC1408_3, UC1409_3, UC1410_3, UC1411_3, UC1412_3, UC1413_3, UC1420_2, UC1420_3, UC1421_3, UC1422_3, UC1423_3, UC1424_3, UC1425_3, UC1513_2, UC1513_3, UC1514_3, UC1515_3, UC1516_3, UC1591_3, UC1592_3, UC1593_3, UC1594_3, UC1595_3, UC1596_3, UC1597_3, UC1598_3, UC1599_3, UC1600_3, UC1601_3, UC1602_3, UC1603_3, UC1604_3, UC1867_3, UC1868_3, UC1871_3, UC1872_3, UC1873_3, UC1944_2, UC1945_2, UC1946_2, UC1947_2, UC1948_2, UC1949_2, UC1950_2, UC1951_2, UC1952_2, UC1953_2, UC1954_2, UC1958_3, UC1959_3, UC1960_3, UC1961_3, UC1962_3, UC1963_3, UC2067_3, UC2068_3, UC2070_3, UC2071_3, UC2072_3, UC2073_3, UC2074_3, UC2075_3, UC2076_3, UC2077_3, UC2078_3, UC2079_3, UC2080_3, UC2081_3, UC2082_3, UC2083_3, UC2084_3, UC2085_3, UC2086_3, UC2087_3, UC2089_3, UC2090_3, UC2091_3, UC2092_3, UC2093_3, UC2094_3, UC2259_2, UC2260_2, UC2261_2, UC2262_2, UC2276_3, UC2280_3, UC2281_3, UC2282_3, UC2288_2, UC2289_2, UC2290_2, UC2291_2, UC2293_2, UC2294_2, UC2295_2, UC2296_2, UC2297_2, UC2298_2, UC2299_2, UC2300_2, UC2306_2, UC2307_2, UC2309_2, UC2310_2, UC2317_3, UC2321_2, UC2322_2, UC2323_2, UC2324_2, UC2325_2, UC2327_2, UC2340_2, UC2341_2, UC2342_2, UC2343_2, UC2344_2, UC2345_2, UC2346_1, UC2347_1, UC2348_2, UC2349_2, UC2350_2, UC2351_2, UC2352_2, UC2353_2, UC2357_3, UC2358_3, UC2359_3, UC2366_3, UC2367_3, UC2410_2, UC2411_2, UC2412_2, UC2413_2, UC2414_2, UC2415_2, UC2515_2, UC2516_2, UC2517_2, UC2518_2, UC2519_2, UC2520_2, UC2521_2, UC2522_2, UC2567_3, UC2568_2, UC2569_2, UC2570_3, UC2574_3, UC2575_3, UC2579_3, UC2580_3, UC2583_1, UC2584_2, UC2585_2, UC2588_2, UC2589_2, UC2590_2, UC2591_2, UC2592_2, UC2593_2, UC2670_3, UC2671_3, UC2678_2, UC2679_2, UC2681_2, UC2682_2, UC2683_2, UC2685_2, UC2686_2, UC2750_3, UC2751_3, UC2752_3, UC2753_3, UC9997_3, UC9998_2, UC9999_3

## Certificats LOE (bc_loe.json)

- 580 certificats amb UC.
- 446 tenen alguna UC a una taula vigent; 264 les hi tenen totes.
- 11 només surten a una taula substituïda (`convalida_anterior`): ELEE0109, EOCJ0109, HOTT0112, IMAR0108, IMAR0208, IMAR0408, INAV0109, SEAD0111, SEAG0108, SSCS0108, TMVB0211.

## Comparació amb `ciclos_fp.json` (relació certificat → cicle de todofp)

- Amb cicle a todofp i al BOE: 337.
- Només al BOE (120): ADGD0110, ADGD0210, ADGN0108, ADGN0110, ADGN0208, ADGN0210, AFDA0110, AFDA0112, AFDA0210, AFDA0212, AFDA0311, AFDA0511, AFDP0111, AGAJ0108, AGAJ0109, AGAR0110, AGAU0211, ARGC0109, ARGG0112, ARGI0209, ARGI0309, ARGN0109, ARGN0110, ARGN0210, ARGT0112, ARGT0411, ARTU0110, COML0111, COMM0111, COMP0108, ELEE0110, ELEE0210, ELEE0310, ELEE0610, ELEM0210, ELEM0311, ELEQ0111, ELEQ0208, ELES0108, ELES0110, ELES0209, ELES0210, ELES0311, ELES0411, ENAE0108, ENAE0408, ENAL0210, ENAS0110, EOCB0108, FMEA0111, FMEM0109, HOTR0109, HOTR0210, HOTU0111, IEXD0308, IEXM0409, IEXM0809, IFCT0409, IFCT0509, IMPE0110, IMPP0308, IMST0210, IMSV0108, IMSV0109, IMSV0208, INAJ0109, MAMA0110, MAMA0210, MAMA0310, MAMD0109, MAMD0110, MAMR0208, MAMR0408, MAPN0111, MAPN0312, MAPN0410, MAPN0510, MAPU0109, MAPU0110, MAPU0409, SANP0108, SEAD0111, SEAD0112, SEAD0212, SEAD0411, SEAD0511, SEAG0108, SEAG0111, SEAG0211, SEAG0311, SSCB0109, SSCB0110, SSCB0209, SSCB0211, SSCE0111, SSCE0112, SSCG0109, SSCG0111, SSCG0209, TCPC0109, TCPF0109, TCPF0111, TCPN0109, TCPN0112, TCPN0412, TCPP0110, TCPP0112, TCPP0212, TCPP0312, TCPP0512, TCPP0612, TCPP0712, TCPP0812, TMVU0212, TMVU0312, TMVU0412, TMVU0512, VICF0110, VICI0109, VICI0110.
- Només a todofp (1): TCPF0309.

## Fora d'abast

- Graus E: 38 cursos d'especialització, 19 amb alguna taula al decret propi. No s'inclouen a l'índex.
- Títols anteriors al sistema d'UC (LOGSE): sense taula; són a la llista de cicles sense taula.
