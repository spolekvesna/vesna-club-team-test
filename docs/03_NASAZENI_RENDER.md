# Nasazení na evidence.spolekvesna.cz

Tento postup je připraven pro netechnickou správkyni s pomocí člověka, který má jednorázově přístup k DNS a Google Workspace/Cloud Console.

## Doporučená architektura

- webová aplikace: Render, region Frankfurt;
- produkční PostgreSQL: Render, Frankfurt, veřejný příchozí přístup vypnutý (`ipAllowList: []`);
- samostatná PostgreSQL DB pro pravidelný test obnovy;
- denní Cron úloha pro backup, v neděli navíc skutečný restore test;
- oddělená kopie záloh v Cloudflare R2 bucketu s jurisdikcí **EU**;
- veřejná adresa pouze `https://evidence.spolekvesna.cz`;
- přihlášení přes Google Workspace Vesny.

Konfigurace je v `render.yaml` a `Dockerfile`.

## Orientační současný základ nákladů (říjen 2026)

Při nejmenších placených plánech použitých v `render.yaml`:

- web 0.5 CPU / 512 MB: cca 7 USD/měsíc;
- produkční PostgreSQL 0.1 CPU / 256 MB: cca 6 USD/měsíc;
- restore-test PostgreSQL 0.1 CPU / 256 MB: cca 6 USD/měsíc;
- cron: minimálně 1 USD/měsíc, jinak dle skutečné doby běhu;
- R2: u malého objemu se pravděpodobně vejde do bezplatného měsíčního rozsahu; nad něj Standard storage 0,015 USD/GB-měsíc.

Základ tedy vychází přibližně na **20 USD/měsíc + případná spotřeba nad limity**. Ceny před objednáním znovu ověřit.

Oficiální zdroje:
- https://render.com/docs/compute-plans
- https://render.com/docs/cronjobs
- https://render.com/docs/blueprint-spec
- https://developers.cloudflare.com/r2/pricing/

## 1. Účet a vlastnictví

Účty Render, Cloudflare/R2 a Google Cloud projekt mají být založeny na organizaci Vesna, ne na soukromém účtu externisty. Zapnout MFA. Recovery údaje uložit podle interních pravidel Vesny.

## 2. Repozitář

Nahrajte tento balík do soukromého Git repozitáře organizace. Nikdy necommitujte `.env`, OAuth secret ani R2 klíče.

## 3. Render Blueprint

V Render Dashboard zvolit New > Blueprint a připojit repozitář. `render.yaml` vytvoří:

- `vesna-club-evidence` web;
- `vesna-club-maintenance` cron;
- `vesna-club-db`;
- `vesna-club-restore-test`.

Při prvním vytvoření vyplnit `sync: false` hodnoty:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `BOOTSTRAP_ADMIN_EMAIL`
- `BACKUP_S3_BUCKET`
- `BACKUP_S3_ENDPOINT`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Pozor: Blueprint může požadovat některé backup secrets zvlášť pro web a cron. Musí být stejné.

## 4. Cloudflare R2 – EU bucket

Při vytvoření bucketu zvolit **Specify jurisdiction > European Union (eu)**. Endpoint bude tvaru:

`https://<ACCOUNT_ID>.eu.r2.cloudflarestorage.com`

Vytvořit token pouze s oprávněním k tomuto bucketu. Bucket není veřejný.

Oficiální dokumentace jurisdikcí: https://developers.cloudflare.com/r2/reference/data-location/

## 5. Google Workspace OAuth

V Google Cloud vytvořit OAuth Client typu **Web application**. Produkční redirect URI musí přesně být:

`https://evidence.spolekvesna.cz/auth/google/callback`

Aplikace požaduje pouze OpenID/email/profile pro identitu, nikoli obsah Google Drive. Uživatel musí současně:

1. mít email v povolené Workspace doméně;
2. existovat v tabulce pracovníků jako aktivní.

Oficiální postup: https://developers.google.com/identity/protocols/oauth2/web-server

## 6. DNS

V Renderu přidat custom domain `evidence.spolekvesna.cz`. U DNS správce `spolekvesna.cz` vytvořit CNAME `evidence` na Render `onrender.com` hostname služby. Render automaticky vydá/obnovuje TLS certifikát.

Dokumentace: https://render.com/docs/custom-domains

Po ověření lze výchozí `onrender.com` subdoménu v Renderu vypnout, aby se aplikace používala jen přes doménu Vesny.

## 7. První správce

Při prvním deployi nastavte `BOOTSTRAP_ADMIN_EMAIL` na Workspace adresu první správkyně. Startup vytvoří účet správce bez lokálního hesla. Další pracovníci se zakládají v aplikaci a poté se přihlašují Workspace identitou.

Po ověření lze bootstrap proměnnou z prostředí odstranit.

## 8. Před ostrými daty

Nejdříve dokončit `docs/05_GDPR_PRED_SPUSTENIM.md`. Až potom vložit skutečná klientská data.
