# 070 — El registre no hauria de revelar quins emails tenen compte

**Estat:** pendent (decisió de producte). **Prioritat:** baixa.
**Origen:** auditoria de seguretat del 2026-10-22, l'única troballa que es va deixar sense arreglar.

## El problema, en una frase

Si algú intenta registrar-se amb un email que ja té compte, la web li respon
"Aquest email ja està registrat". Així, qualsevol persona pot comprovar si un
email concret és usuari de GrausFP.

## Per què importa (poc)

- Només revela una cosa: que *aquell* email té compte. No dona accés a res.
- Però contradiu el que ja fan les altres pantalles: el login i "He oblidat la
  contrasenya" responen sempre el mateix, existeixi o no el compte, justament
  per no revelar-ho.
- Pot servir per preparar un correu de pesca ("t'escrivim de GrausFP…") dirigit
  a algú que sabem que és usuari.

## On és

`backend/app.py`, funció `auth_register`: la línia que retorna
`{"error": "Aquest email ja està registrat"}` amb codi `409`.

## Per què no s'ha fet encara

Arreglar-ho canvia el que veu l'usuari, i cal decidir com:

- **Opció A (la recomanada):** respondre igual que un registre nou ("Revisa el
  teu email") i enviar a l'email existent un missatge tipus *"Ja tens compte a
  GrausFP. Si no recordes la contrasenya, fes servir aquest enllaç per
  recuperar-la."* És el que fan la majoria de webs. Inconvenient: cal un
  email nou (text en català i castellà) i qui s'equivoca no ho veu a la
  pantalla, sinó al correu.
- **Opció B:** deixar-ho com està i acceptar el risc, que és baix.

## Si es fa (opció A)

1. A `auth_register`, quan l'email ja existeix: no crear res, enviar el correu
   "ja tens compte" i retornar el mateix `201` i el mateix missatge que un
   registre nou.
2. Afegir la funció d'email a `backend/email_service.py` (copiar l'estil de
   `send_password_reset_email`).
3. El límit de 20 registres per hora i IP que ja hi ha (commit `a8c9546`)
   evita que això serveixi per inundar bústies.
4. Test: registrar dues vegades el mateix email → les dues respostes són
   idèntiques i la segona envia el correu "ja tens compte".
5. Revisar `frontend/register.html`: ara mostra l'error del 409; amb el canvi
   ja no rebrà mai aquest error.

## Referència

Informe complet de l'auditoria (fora del repo):
`~/security-audit-skill/cercador-grausfp/run-1/REPORT.md`
— troballa `backend/app.py:auth_register:409-account-enumeration`.
