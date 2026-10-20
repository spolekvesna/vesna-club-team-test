# Provozní návod pro správkyni

## Pracovníci

`Pracovníci` > přidat email, jméno a roli. Deaktivace znemožní další přístup, ale historické záznamy zůstanou přiřazené původnímu pracovníkovi.

Role:
- **správce** – vše včetně pracovníků, číselníků, importu, auditů a záloh;
- **pracovník** – klienti, výkony, skupiny, denní zápisy, osobní kontrolní report;
- **čtenář/reporting** – agregované indikátory a jejich auditovatelný zdroj pouze s interními kódy osob.

## Číselníky

Položku lze přidat, přejmenovat, změnit pořadí/nadřazenou oblast, aktivovat/deaktivovat a hromadně vyřadit. Použitou položku nelze fyzicky smazat.

Při slučování duplicit systém přesměruje současné vazby na cílovou položku. Staré výkony si ve snapshotu zachovávají název platný v okamžiku zápisu.

## Klienti

Při založení klienta aplikace varuje při shodě jména, příjmení a data narození. Karta klienta obsahuje:
- historii individuálních výkonů;
- skupinové účasti;
- dokumentová metadata;
- součty a rozpad KA;
- filtry časové osy;
- audit změn základní karty.

## Skupinové akce

Zakládejte **jednu akci** a v ní označte více klientů/pracovníků. Host bez klientské karty je neprojektový a nevstupuje do osobních indikátorů.

Pro občanskou orientaci systém automaticky přidá 026200; jiné specifické indikátory se označují explicitně. Uvádějte referenci na prezenční listinu, pokud existuje.

## Denní zápisy

Kalendář ukazuje počet zápisů v daném dni. V jednom dni může být více záznamů. Autor může svůj zápis upravit; správce může upravit všechny. U editace se vede historie a souběžná kolize je odmítnuta místo přepsání.

## Indikátory

`Indikátory a výstupy` ukazují výsledek, cíl a u osobních 026* rozkliknutelné zdrojové elektronické záznamy. 026000 deduplikuje klienta napříč všemi způsobilými podporami.

Kontrolní výpis je určen pracovníkovi/správci. Lze filtrovat období, KA/podaktivitu, pracovníka, oblast, činnost, typ akce, stav klienta a indikátor a exportovat CSV/XLSX.

## Zálohy

Automatická úloha běží denně. Správce vidí historii, datum poslední úspěšné zálohy a poslední úspěšný test obnovy. Jednou týdně se má záloha skutečně obnovit do oddělené DB.

Pokud záloha nebo restore test hlásí chybu, nepovažujte stav za „máme zálohu“. Chybu řešit bez odkladu.

## Nouzový postup při nedostupnosti

1. Nezadávat klientská data do náhradních soukromých tabulek/mailů.
2. Zapsat začátek výpadku a dotčené uživatele.
3. Ověřit stav Render/Cloudflare/Google Workspace.
4. Pokud je podezření na únik/neoprávněný přístup, přejít na incident postup v `10_INCIDENT_POSTUP.md`.
5. Po obnovení provozu doplnit legitimní papírové záznamy řízeně a označit je jako přepsané z listiny.

## Důležitá pojistka produkčních záloh

V `APP_ENV=production` aplikace nepovažuje lokální soubor na instanci za platnou zálohu. Pokud není nastaven `BACKUP_S3_BUCKET`, zálohovací úloha skončí chybou. Smyslem je zabránit falešnému pocitu bezpečí na hostingu, kde může být lokální disk instance dočasný.
