# Vesna Club – evidence klientů a výkonů

Interní víceuživatelská webová aplikace podle `ZADANI_PRO_VYVOJ_AI.md` z balíčku Vesna Club 2026-10-13.

## Co je implementováno

- klientské karty s časovou osou, filtry, součty a dokumenty jako metadata/odkaz na omezený Google Drive;
- individuální výkony včetně KA/podaktivity a všech číselníkových polí;
- KA1/KA2 skupinové akce s jednou akcí a více účastníky/pracovníky;
- KA3.1/3.2/3.3 s konfigurovatelnými upozorněními na hodinový limit, nikoli tvrdou blokací;
- kalendář denních zápisů, více zápisů za den, autor a historie změn;
- správa pracovníků a rolí `admin`, `worker`, `reader`;
- správa kategorií a 216 výchozích číselníkových položek přímo v aplikaci, včetně aktivace/deaktivace a slučování;
- audit změn a optimistické zamykání proti tichému přepsání souběžných úprav;
- indikátory 026000, 026200, 026300, 026400, 026510, 026600, 026610, 028309, 028313;
- zdrojové elektronické záznamy pro kontrolu indikátorů proti papírovým listinám;
- kontrolní výpis evidence s filtry a CSV/XLSX exportem včetně metadat filtrů;
- idempotentní XLSX import s náhledem a varováním u nejednoznačných historických výkonů;
- automatické databázové zálohy, retence, oddělené objektové úložiště a skutečný test obnovy;
- responzivní rozhraní pro počítač a telefon;
- Google Workspace OAuth pro produkční přihlášení.

## Lokální spuštění

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

V development režimu aplikace vytvoří tři syntetické testovací účty:

- `admin@example.test`
- `worker@example.test`
- `reader@example.test`

Testovací heslo je uvedeno na lokální přihlašovací obrazovce / v testovacím kódu a **produkční lokální přihlášení je vypnuté**.

Syntetická demo data lze doplnit:

```bash
python scripts/seed_demo.py
```

Skript odmítne běžet s `APP_ENV=production`.

## Testy

```bash
PYTHONPATH=. DATABASE_URL=sqlite:///./runtime/test.db APP_ENV=test pytest -q
```

Akceptační testy pokrývají mimo jiné unikátní osoby v indikátorech, souběžné editace, role, prezenční listiny, historii denních zápisů, číselníky, import, export a zálohu/obnovu.

## Produkce

Doporučený deployment je připraven v `render.yaml` a `Dockerfile`. Produkce vyžaduje:

1. organizací vlastněný účet u hostingu a zálohovacího úložiště;
2. PostgreSQL, nikoli SQLite;
3. Google Workspace OAuth a předem založené aktivní pracovníky;
4. DNS pro `evidence.spolekvesna.cz`;
5. EU zálohovací bucket a přístupové klíče;
6. právní/GDPR kontrolu a smluvní nastavení zpracovatelů;
7. poslední porovnání živého Google sešitu s dodaným XLSX a řízený ostrý import.

Podrobný postup je v `docs/`.

## Bezpečnostní zásady

- žádná skutečná klientská data nejsou součástí repozitáře ani demo seedu;
- role jsou kontrolované na serveru;
- `reader` ve výchozím stavu nevidí klientské karty, denní poznámky ani osobní kontrolní export;
- použité číselníkové položky se fyzicky nemažou; historické výkony si nesou snapshot názvů;
- citlivé dokumenty se do aplikace nenahrávají, evidence uchovává pouze metadata/odkaz do omezeného úložiště;
- export není považován za zálohu databáze.

## TEAM TEST varianta

Pro dočasné týmové testování bez vlastní domény použijte `render.yaml` a návod `START_TADY_TEAM_TEST.md`.
Původní produkční Render Blueprint je zachován jako `render-production.yaml`.
