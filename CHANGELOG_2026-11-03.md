# Vesna Club – změny podle týmového testování (3. 11. 2026)

Zapracováno podle dokumentu `Bugs.docx` z týmového testu.

## Opravené chyby
- Dokumenty klienta jsou z karty klienta přímo zobrazitelné/upravitelné; odkaz na Google Disk je otevřitelný, pokud je uveden.
- Podaktivita je navázána na KA: KA2 nabízí 2.1–2.4, KA3 nabízí 3.1–3.3. Server zároveň odmítne neplatnou kombinaci.

## Klienti a karta klienta
- Nové nepovinné pole Přezdívka; interní kód zůstává technicky zachován, ale v běžných seznamech se nezobrazuje.
- Seznam klientů lze filtrovat podle stavu monitorovacího listu Ano/Ne.
- `Scan/doklad` přejmenován na `Monitorovací list` a běžné UI nabízí pouze Ano/Ne.
- Klienti jsou řazeni podle přezdívky (pokud je vyplněna), jinak podle jména.
- Souhrnné dlaždice na kartě klienta jsou klikací filtry: individuální podpora, skupinové účasti, dokumenty, návazné kroky.
- Zapojení do KA/podaktivit je klikací rychlý filtr.
- Filtr historie používá výběr z KA/podaktivit místo volného textu.
- Z časové osy lze přímo otevřít/upravit individuální výkon, dokument a konkrétní účast klienta ve skupinové akci.
- U skupinové akce lze upravit účast konkrétní osoby (přítomnost, projektová způsobilost, přepis z prezenční listiny), aniž by se měnila společná akce ostatním.

## Přehled a evidence
- Dlaždice na Přehledu fungují jako rychlé filtry.
- Filtr KA/podaktivity u individuálních výkonů i kontrolního výpisu je číselník, nikoli volný text.
- Zobrazená data používají český formát data `dd.mm.rrrr` na hlavních výpisech a detailech.

## Kroužky a skupiny
- `Klub a skupiny` přejmenováno na `Kroužky a skupiny`.
- Přidán filtr podle data a typu akce.
- Typy akcí rozšířeny o Program pro děti, Program pro mládež a Mezikulturní otevřenou akci.
- `Komunitní akce` přejmenována na `Komunitní a rodinný integrační program`.
- Výběr projektových účastníků je abecedně řazený, bez interních kódů a má vyhledávací pole podle jména/přezdívky.

## Dokumenty a výstupy
- Text u dokumentů vysvětluje, že elektronický scan je nepovinný; papírový monitorovací list je možný bez ukládání scanu do systému.
- `Projektové agregáty` přejmenovány na `Projektové indikátory a výstupy`.
- U projektových dokumentů je uložený webový odkaz přímo klikací.
- Typ skupinové akce v kontrolním výpisu používá české názvy.

## Databáze
- Přidána migrace `b71f4c2a1d90_client_nickname.py` pro nepovinnou přezdívku klienta.
- Migrace je dopředně kompatibilní a nemaže existující testovací data.

## Ověření
- 27/27 automatických testů prošlo.
- Čisté `alembic upgrade head` prošlo.
- `alembic check` nehlásí chybějící migrace.
- Smoke test: `/health`, login, Přehled, Klienti, Individuální podpora, Kroužky a skupiny, Kontrolní výpis a Projektové indikátory a výstupy vracejí HTTP 200.

## Doplnění při ověření před nasazením
- Filtr KA na kartě klienta zahrnuje i příslušné podaktivity.
- Filtr monitorovacího listu Ne zahrnuje i starší záznamy s neurčeným stavem, které se v přehledu zobrazují jako Ne.
- Při dočasném označení posledního účastníka jako nepřítomného se zachovají vybrané indikátory; po obnovení účasti se klient opět započítá.
- Ověřeno zachování všech původních řádků v 17 tabulkách při aktualizaci z předchozí databázové verze na SQLite.
