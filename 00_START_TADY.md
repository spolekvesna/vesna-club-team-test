# VESNA CLUB – TEAM TEST: START TADY

Tento balíček je připravený tak, aby **aplikaci nasadil jednou jeden člověk** a všichni ostatní členové týmu už jen otevřeli odkaz v prohlížeči. Na počítače ani telefony týmu se nic neinstaluje.

> **DŮLEŽITÉ:** TEAM TEST je pouze pro fiktivní/syntetická data. Nevkládejte skutečná jména klientů, telefonní čísla, e-maily, adresy, zdravotní nebo sociální údaje ani jiné osobní údaje.

## A. Jednorázové spuštění – udělá správce testu

### 1. Rozbal balíček

Rozbal ZIP do běžné složky. Uvnitř musí být v hlavní úrovni mimo jiné soubor `render.yaml`, `Dockerfile`, složka `app` a tento návod.

### 2. Založ soukromý repozitář na GitHubu

1. Přihlas se na https://github.com účtem, který může Vesna dlouhodobě používat.
2. Vpravo nahoře klikni na **+ → New repository**.
3. Název: `vesna-club-team-test`.
4. Viditelnost nastav na **Private**.
5. Nezaškrtávej vytvoření README, `.gitignore` ani licence – vše už je v balíčku.
6. Klikni na **Create repository**.
7. V novém prázdném repozitáři zvol **Add file → Upload files** (nebo odkaz pro nahrání existujících souborů).
8. Přetáhni do okna **obsah rozbalené složky**, ne samotný ZIP. GitHub umí přes web nahrát i složky.
9. Zkontroluj, že `render.yaml` je přímo v kořeni repozitáře, nikoli o jednu složku níž.
10. Dole potvrď **Commit changes**.

### 3. Připoj Render

1. Otevři https://render.com a přihlas se / vytvoř účet, ideálně účet spravovaný Vesnou.
2. Pokud Render požádá o propojení GitHubu, povol mu přístup pouze k repozitáři `vesna-club-team-test`.
3. V Render Dashboard zvol **New → Blueprint**.
4. Vyber repozitář `vesna-club-team-test`.
5. Render automaticky načte `render.yaml`.

### 4. Zkontroluj, co Render vytvoří

Měly by se objevit dvě položky:

- webová služba **`vesna-club-team-test`**, plán **Free**, region **Frankfurt**;
- databáze **`vesna-club-team-test-db`**, PostgreSQL, plán **Free**, region **Frankfurt**.

Nic dalšího není třeba ručně vyplňovat. Tajný klíč aplikace se vygeneruje automaticky a databázové spojení se propojí z Blueprintu.

### 5. Spusť nasazení

1. Klikni **Deploy Blueprint / Apply** (pojmenování se může v rozhraní Renderu mírně lišit).
2. Počkej, až webová služba dostane stav **Live**.
3. Otevři její adresu ve tvaru `https://vesna-club-team-test-xxxx.onrender.com`.
4. Při prvním otevření může načtení chvíli trvat – aplikace zakládá databázi a syntetická demo data.
5. Pokud vidíš přihlašovací stránku s výrazným označením **TESTOVACÍ VERZE**, je spuštění hotové.

## B. Přihlášení pro tým

### Správce
- uživatel: `admin@example.test`
- heslo: `VesnaDemo!2026`

### Pracovník
- uživatel: `worker@example.test`
- heslo: `VesnaDemo!2026`

### Čtenář / reporting
- uživatel: `reader@example.test`
- heslo: `VesnaDemo!2026`

Doporučení: běžným testerům dej hlavně účet **pracovníka**. Správce má zkoušet číselníky, pracovníky a nastavení. Účet čtenáře použijte k ověření omezených práv.

## C. Co má tým udělat

Tým už nic neinstaluje. Stačí:

1. otevřít sdílený odkaz v Chrome/Edge/Safari;
2. přihlásit se testovacím účtem;
3. pracovat pouze s vymyšlenými osobami a údaji;
4. projít soubor `02_CHECKLIST_PRO_TYM.md`;
5. u chyb poslat screenshot, použitou roli, co uživatel udělal a co očekával.

## D. Co je v TEAM TESTU schválně zjednodušené

- není potřeba doména `spolekvesna.cz`;
- není zapnuté přihlášení přes Google Workspace;
- nejsou použita skutečná klientská data;
- není zapnutý produkční systém externích záloh;
- používá se bezplatná PostgreSQL databáze;
- web se po delší nečinnosti uspí a první otevření potom může být pomalejší.

## E. Důležitá omezení bezplatné verze Renderu

- Free web se po 15 minutách bez návštěvy uspává; další otevření jej probudí a může trvat přibližně minutu.
- Free PostgreSQL databáze má limit 1 GB a po 30 dnech expiruje. Není určena pro ostrý provoz a Render pro ni neposkytuje databázové zálohy.
- Testovací data proto berte jako dočasná. Nic, co potřebujete archivovat, do TEAM TESTU nepatří.

## F. Když něco nejde

### Odkaz dlouho „načítá“
Po nečinnosti je to u Free plánu normální. Počkej přibližně minutu a stránku znovu načti.

### Render hlásí, že nenachází `render.yaml`
Na GitHubu je pravděpodobně celý balík vložený jako jedna nadřazená složka. `render.yaml` musí být vidět hned na hlavní stránce repozitáře.

### Render nevidí soukromý repozitář
V nastavení připojení GitHubu povol Renderu přístup k repozitáři `vesna-club-team-test`.

### Aplikace ukazuje chybu při prvním deployi
V Renderu otevři webovou službu → **Logs**. Zkopíruj poslední část chybového výpisu a pošli ji spolu s informací, že jde o TEAM TEST.

### Testovací databáze po čase zmizela
Free PostgreSQL expiruje po 30 dnech. Pro další testovací kolo se vytvoří nová databáze / nový TEAM TEST. Skutečný provoz bude používat persistentní placenou databázi a zálohy.

## G. Co TEAM TEST už umí

- více lidí může současně používat společná data;
- klientské karty a historie výkonů;
- individuální výkony a KA1/KA2/KA3;
- jedna skupinová akce s více účastníky;
- denní zápisy v kalendáři, včetně více zápisů za den a historie editací;
- pracovníci a role;
- upravitelné číselníky přímo v systému;
- ochrana historických výkonů při změně/deaktivaci číselníku;
- ochrana proti tichému přepsání při souběžné editaci stejného záznamu;
- indikátory s dohledáním zdrojových elektronických záznamů;
- CSV/XLSX kontrolní výstupy;
- responzivní použití na počítači i telefonu.

## H. Funkční poznámky, které nejsou chyba

- Hodinové limity KA3 jsou v TEAM TESTU **upozornění**, nikoli tvrdá blokace. Je to záměr podle zadání.
- Číselník, který už byl použit v historii, se nemá „vymazat z minulosti“. Správce jej může deaktivovat nebo upravit; historický záznam zůstává čitelný.
- Čtenář/reporting nemá mít přístup ke klientským kartám ani detailním osobním exportům. Je to bezpečnostní omezení, ne chyba.
- Klientské dokumenty se v této verzi neevidují jako nahrané citlivé soubory do aplikace; systém pracuje s metadaty/odkazem na řízené úložiště.
- U indikátorů se jedna osoba zapojená do více relevantních aktivit nemá započítat opakovaně.

## I. Kdy TEAM TEST ukončit

TEAM TEST je určený k připomínkování logiky a použitelnosti. Jakmile tým odsouhlasí strukturu, přejde se na produkční konfiguraci: Google Workspace, `evidence.spolekvesna.cz`, persistentní PostgreSQL, externí zálohy a restore test, finální GDPR/provozní kontrola a řízený import skutečných dat.
