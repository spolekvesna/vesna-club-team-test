# Zdroje a implementační rozhodnutí

## Závazné podklady

1. `ZADANI_PRO_VYVOJ_AI.md` – hlavní specifikace a akceptační kritéria.
2. `CTI_ME_NEJDRIV.md` – organizační zadání: AI má dodat spustitelnou aplikaci, ne pouze návrh.
3. `Vesna evidence klientu - data.xlsx` – výchozí struktura dat a číselníků.
4. projektové přílohy `01-Projekt-ISKP.pdf`, `02-KA2.pdf`, `05-KA1-opraveno.pdf`, `07-KA3.pdf`, `12-PZP-obecna-cast-v5.pdf`.
5. `puvodni_offline_prototyp_2026-09-29.html` – pouze vzor logiky/vzhledu, nikoli technický základ.

## Potvrzené věcné závěry

- Číselník má 216 položek: 14 oblastí, 118 činností a 84 dalších položek. Původní ID se zachovávají.
- KA1 = klub; KA2 = skupinové/komunitní aktivity; KA3 obsahuje 3.1 kariérní/vzdělávací poradenství, 3.2 mentoring a 3.3 psychologické poradenství.
- Zdrojové projektové podklady formulují u KA3.1 + 3.2 limit 10 hodin/klient a u 3.3 vlastní limit 10 hodin/klient. Protože zadání výslovně požaduje nezdědit automaticky výklad starého prototypu, aplikace používá nastavitelné **upozornění**, nikoli blokaci.
- 026000 je počet unikátních podpořených osob napříč způsobilými KA. Jedna osoba se nezapočítá opakovaně.
- 026200 a další specifické indikátory nevznikají jen z obecné oblasti/činnosti; musí mít explicitní zdrojový záznam nebo schválené pravidlo.
- Anonymní cíl užitečnosti/zpětné vazby je veden odděleně od 026510, dokud nebude schválena metodika převodu.

## Bezpečné výchozí volby

- Produkční DB: PostgreSQL.
- Vývoj/test: SQLite.
- Přihlášení produkce: Google Workspace domény `spolekvesna.cz` + předem povolený aktivní pracovník v aplikaci.
- Dokumenty klientů: metadata a reference do omezeného Google Drive, nikoli veřejné odkazy ani upload skenů do webové aplikace.
- `reader/reporting`: pouze agregované reporty a interní kódy osob v auditovatelných zdrojích; bez jmen a klientských karet.
- Souběžné editace: optimistická verze záznamu, konflikt HTTP 409.

## Otevřené rozhodnutí před ostrým importem

Starý list `Vykony` v dodaném XLSX neobsahuje pole KA ani podaktivita. Aplikace proto při migraci takový výkon označí `legacy` a zobrazí varování. **Nehádá KA3.** Před ostrým vykazováním musí správkyně určit mapování nebo historické řádky ručně doplnit.
