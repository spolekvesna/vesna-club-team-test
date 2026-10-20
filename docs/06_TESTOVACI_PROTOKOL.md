# Testovací protokol

Datum sestavení balíku: 20. 10. 2026.

## Automatizované akceptační testy

Spouští se:

```bash
PYTHONPATH=. DATABASE_URL=sqlite:///./runtime/test.db APP_ENV=test pytest -q
```

Pokryté scénáře:

1. přesně 216 výchozích číselníkových položek, 14 oblastí a 118 činností;
2. jedna osoba v několika KA se v 026000 započítá jen jednou;
3. specifický indikátor nevznikne z obecného výkonu bez explicitního zdroje;
4. deaktivace použité číselníkové položky nezničí historický výkon;
5. souběžná editace stejného klienta vrátí konflikt 409 a první změnu nepřepíše;
6. role reader nemá administraci;
7. kalendář a základní CSV export fungují;
8. databázová záloha vznikne a lze ji skutečně obnovit do oddělené SQLite DB;
9. import je idempotentní;
10. reader nemá klientské karty ani kontrolní report a v indikátoru nevidí jméno;
11. papírová prezenční listina se dá dohledat u 026200 a opakovaná osoba se neduplikuje;
12. nezpůsobilý výkon po přepnutí nezanechá specifický indikátor;
13. jeden den podporuje více denních zápisů a editace vytvoří auditní historii;
14. XLSX kontrolní export obsahuje list s metadaty filtrů;
15. 028309 a 028313 se počítají samostatně a anonymní zpětná vazba se nevydává za 026510;
16. oblast s podřízenými činnostmi nelze fyzicky smazat;
17. import historických výkonů bez KA zobrazuje varování a používá `legacy` místo vymyšlené KA.

## Předprodukční ruční akceptace

Po nasazení na testovací URL ještě provést s 2–3 lidmi z Vesny:

- telefon + notebook: založení klienta, výkonu, skupinové akce a denního zápisu;
- dva lidé současně otevřou stejný záznam a jeden změnu uloží dřív;
- odhlášený uživatel a reader zkusí přímou URL chráněné sekce;
- správce deaktivuje číselníkovou položku použitou v demo výkonu a ověří historii;
- vytvořit backup, vyvolat restore test a zkontrolovat stav `ok`;
- importovat poslední kopii sešitu nejprve pouze jako preview a porovnat počty;
- porovnat vzorek papírové prezenční listiny s elektronickým zdrojovým reportem indikátoru;
- projít rozhraní na šířce telefonu a ověřit, že všechny formuláře jsou použitelné bez desktopového zoomu.

## Provozní smoke testy release

Před zabalením release se navíc ověřuje:

- migrace Alembic od úplně prázdné databáze;
- `alembic check` bez chybějících migrací;
- syntetický demo seed na čisté databázi;
- `/health` a přihlašovací stránka přes skutečný FastAPI lifespan;
- vytvoření databázové zálohy a skutečná obnova/test obnovení;
- produkční konfigurace bez `BACKUP_S3_BUCKET` musí zálohu odmítnout jako chybu (fail-closed);
- syntaktická validace `render.yaml`;
- kompilace Python zdrojů;
- kontrola release na známé reálné osobní údaje a omylem vložené secrets.

Docker image nebylo možné v pracovním prostředí lokálně sestavit, protože zde není dostupný Docker daemon/CLI. `Dockerfile` a Render Blueprint jsou součástí release a Render image při nasazení sestaví. Tato skutečnost není vydávána za provedený Docker build.
