# Investigació: fonts de cursos programats fora de Catalunya (pla 104)

Data: 2026-11-27. Només lectura i poques peticions per font (entre 1 i 6). Cap codi de producció tocat.
Cap dada del projecte ni del propietari enviada a cap servei.

## Recomanació

**Fer-ho només amb el cercador estatal de Fundae.** És una sola font, es llegeix amb una petició,
porta el codi d'especialitat del SEPE i el 69 % dels cursos són de teleformació. Les comunitats
autònomes, de moment, no: cada una és un format diferent i les dues més grans que tenen dades obertes
(Madrid i País Basc) no porten prou informació per a una alerta fiable.

Mida estimada del pla d'implementació: **M** (semblant als plans 099 i 102 junts, però reaprofitant-ne
les peces). No l'he escrit: espera el vistiplau.

## 1. El cercador estatal SEPE–Fundae

- **Adreça:** `https://experienciafundae.es/formacion-subvencionada` (l'enllaça la notícia del SEPE del
  25-9-2025). És una aplicació que demana les dades a `https://agora.fundae.es`.
- **Per què «no responia»:** no és cap bloqueig. El certificat de `agora.fundae.es` i de
  `www.fundae.es` és de la FNMT («AC SERVIDORES SEGUROS TIPO2 G2R») i el servidor no envia el certificat
  intermedi. Els navegadors el resolen sols; `curl` i Python el rebutgen («unable to get local issuer
  certificate»). Solució: donar a `requests` el certificat intermedi de la FNMT (`verify=`), sense
  desactivar la verificació. **No provat des del VPS.**
- **Es pot llegir automàticament:** sí. Sense sessió, sense clau i sense captcha. Provat des d'un
  navegador (que valida el certificat); amb `requests` cal el pas anterior.
- **Peticions:**
  - `GET /Buscador/BuscarRecursosFormativosFundaeSEB?idCatalogo=3` → tot el catàleg d'un cop (1,5 MB).
  - `GET /Oferta/RecuperarDifusionesRFO?idModalidad=<1|2|3>&codigoTitulacion=<codi>` → els centres que
    l'imparteixen.
  - La web també envia un `POST /Buscador/AltaHistorialBusquedas` a cada cerca (registre de cerques);
    un lector automàtic no l'ha de fer.
- **Volum (27-11-2026):** 1.089 cursos de 933 especialitats. La web anuncia «més de 2.100 cursos»
  sumant altres catàlegs (eFundae, beques de Google i IBM…), que no són formació subvencionada.

| Modalitat | Cursos |
|---|---|
| Teleformació | 750 |
| Presencial | 325 |
| Mixta | 14 |

- **Encaix amb el nostre catàleg:** 927 dels 933 codis són a `sepe_especs.json`. Els 6 que no hi són
  comencen per `IT` (`ITADG0006`…).
- **Camps del catàleg:** codi d'especialitat (`codigoTitulacion`), denominació, objectius, modalitat,
  hores, províncies, àrees d'interès, si és formació habilitant (32) i si la inscripció és oberta
  (totes).
- **Camps de la fitxa (per centre):** entitat i centre, adreça, població, província, telèfon i correu,
  termini de preinscripció (dates) i **mes i any d'impartició** (no el dia). L'enllaç públic de cada
  curs és `https://experienciafundae.es/ficha-curso/oferta/<modalitat>/<codi>`.
- **Mostra:** `ADGD0003` «Dirigir equipos de trabajo en entornos virtuales», teleformació, 30 h. Cinc
  centres, tots de Madrid; per exemple, preinscripció de l'1-10-2026 al 30-11-2026 i impartició el
  novembre del 2026.
- **On són els centres:** Madrid surt a 521 cursos, Màlaga a 280, Valladolid a 174, Sevilla a 126.
  Barcelona, a 46. Amb alguna província catalana n'hi ha 56 (31 de teleformació i 25 presencials).

### Sense comprovar

- **Si un curs de teleformació admet alumnes de qualsevol província.** La fitxa dona la província del
  centre i la web deixa filtrar per província, però no diu qui s'hi pot inscriure. És la premissa de
  tota la idea i cal confirmar-la abans d'escriure el pla (a les bases de la convocatòria o trucant a
  un centre).
- **Condicions d'ús.** El lloc no té `robots.txt` (torna la pàgina principal) i no he llegit l'avís
  legal.
- **Cada quant canvia.** Només n'he vist una instantània.

## 2. Teleformació: n'hi ha prou?

Sí per començar: 750 especialitats amb algun curs de teleformació obert, sobre les 7.557 del catàleg.
Són sobretot d'Administració i gestió (267 cursos comptant totes les modalitats), Comerç (129), Serveis
socioculturals (102) i Informàtica (100).

## 3. Comunitats autònomes

Fundae enllaça els 17 serveis d'ocupació a `experienciafundae.es/mas/oferta-formativa-ccaa`.

| Comunitat | Font | Volum | Codi d'especialitat | Dates | Valoració |
|---|---|---|---|---|---|
| Madrid | Dades obertes (JSON i CSV) | 7.628 | Sí, a totes les files | **No** | Sense dates no serveix per avisar d'un curs nou. Els codis de curs són de la programació del 2024 |
| País Basc (Lanbide) | Dades obertes (JSON) | 1.388 | Dins del títol, a 1.160 | Sí | La millor de les autonòmiques, però els codis porten un sufix propi (`FCOV0002HV`): només 753 casen amb el nostre catàleg |
| Múrcia | API pròpia (JSON) | 1.937 | **No** (8 de 1.937) | Només a 453 | No es pot lligar amb les especialitats |
| Navarra | Dades obertes | 4 | No | Sí | Conjunt de mostra, buit a la pràctica |
| Canàries | RSS | — | — | — | No respon (temps esgotat) |
| Castella-la Manxa | Només pàgines de cerca | — | — | — | Caldria llegir HTML |
| Andalusia | Oficina virtual (aplicació web) | — | — | — | Cap conjunt de dades obert trobat. No investigat a fons |
| País Valencià (LABORA) | Portal web | — | — | — | Cap conjunt de dades obert trobat. No investigat a fons |
| Madrid, cercador viu (Via Laboris) | Pàgina web | — | — | — | No investigat a fons |

A Madrid, les 7.628 files es reparteixen en 3.262 d'especialitats del catàleg SEPE, 3.460 de certificats
(Graus C del pla antic) i 906 amb variants del codi (`ADGD015PO1`, `IFCT78_1`). 2.954 són de
teleformació.

**Conclusió:** de les tres comunitats grans que demanava el pla, cap és fàcil. Madrid té dades però
sense dates; Andalusia i el País Valencià no en publiquen d'obertes. Afegir-ne una voldria dir un
analitzador i un manteniment propis per a cada una.

## 4. Dades obertes

No hi ha cap conjunt estatal a datos.gob.es amb l'oferta programada. Sí que n'hi ha d'autonòmics: els
de la taula anterior i els de Catalunya.

**Troballa a part:** a les dades obertes de la Generalitat hi ha dos conjunts del Consorci per a la
Formació Contínua de Catalunya («accions formatives programades» i «previstes») que no fem servir. No
els he mirat: són de Catalunya i queden fora d'aquest pla.

## Què faria el pla d'implementació (esborrany, per decidir)

1. Un lector del catàleg de Fundae dins del refresc setmanal (una petició), no fatal, amb el certificat
   de la FNMT.
2. A la fila de cada especialitat SEPE, un indicador «Cursos subvencionats oberts» amb la modalitat, i
   un panell amb els centres. El detall es demanaria en obrir-lo, amb memòria cau, com ja fem amb les
   entitats (pla 099).
3. L'alerta «avisa'm quan hi hagi un curs d'aquesta especialitat a l'Estat», amb filtre de només
   teleformació. Compararia el catàleg d'una setmana amb el de l'anterior, com l'alerta d'entitats del
   pla 102.
4. Documentar-ho a `fonts.html` i a «Per què GrausFP?».

Abans d'escriure'l cal resoldre el primer punt de «Sense comprovar».

## Materials

Les mostres baixades són en una carpeta temporal de la sessió i no es conserven. Tot el que s'hi va
mesurar és en aquest informe.
