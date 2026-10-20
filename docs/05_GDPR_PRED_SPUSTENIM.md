# GDPR a ochrana dat – checklist před ostrým spuštěním

Toto není právní stanovisko. Je to technicko-organizační checklist z projektového zadání; finální právní posouzení musí udělat Vesna / její pověřená osoba.

## 1. Role a účel

- potvrdit, že Vesna je správcem osobních údajů v této evidenci a identifikovat případné další správce/společné správce;
- pro každou skupinu dat sepsat účel a právní titul;
- zvlášť posoudit data dětí/mladistvých a roli rodiče/zákonného zástupce;
- určit, která pole jsou opravdu nutná; nepotřebná pole nezapínat jen proto, že je systém umí.

## 2. Zpracovatelé a umístění dat

Před vložením reálných dat prověřit a archivovat aktuální smluvní dokumentaci/DPA a seznam subzpracovatelů minimálně pro:

- Render (hosting + PostgreSQL);
- Cloudflare (R2 zálohy, pokud bude zvolen);
- Google Workspace/Drive (identity a dokumentové úložiště).

Ověřit přenosy mimo EHP, jejich mechanismus a zda odpovídají interním pravidlům/projektovým podmínkám. Samotné „server je ve Frankfurtu“ není kompletní GDPR analýza dodavatelského řetězce.

## 3. Přístupy

- každý pracovník vlastní účet, žádné sdílené login údaje;
- MFA na infrastrukturních administrátorských účtech;
- pravidelně kontrolovat seznam aktivních pracovníků a role;
- při odchodu člověka účet okamžitě deaktivovat; historie se nesmí mazat;
- čtenář/reporting bez osobních klientských detailů, pokud k nim nemá výslovný důvod.

## 4. Uchování a mazání

Stanovit retenční lhůty zvlášť pro:
- klientské identifikační údaje;
- výkonovou evidenci a projektové doklady;
- denní zápisy;
- audit log;
- importní soubory;
- zálohy (technický návrh je 35 dnů, musí se sladit s právní/projektovou potřebou).

Doplnit postup ukončení projektu a výmazu/anonymizace po skončení zákonných/projektových lhůt.

## 5. Informační povinnost

Připravit informační text pro dospělého klienta a pro dítě/rodiče podle skutečných účelů a titulů. Návrhová osnova je v `09_INFORMACNI_TEXT_NAVRH.md`.

## 6. DPIA / posouzení rizik

Před spuštěním zdokumentovat, zda je potřeba posouzení vlivu na ochranu osobních údajů (DPIA). Zohlednit zejména zranitelné osoby, děti, rozsah a povahu poznámek, kombinaci identifikačních a sociálních údajů a dobu zpracování.

## 7. Technické minimum před daty

- HTTPS a ověřená vlastní doména;
- Google Workspace login, lokální login vypnut;
- PostgreSQL neveřejná z internetu;
- EU-jurisdiction bucket pro druhou kopii záloh;
- úspěšná záloha a úspěšný test obnovy;
- role otestované třemi testovacími účty;
- žádná reálná data v logu/build artefaktech/Git repozitáři;
- poslední kontrola exportů, že neobsahují více údajů, než je potřeba.

## 8. Projektové požadavky

Zadání upozorňuje, že přiložené PZP obsahují velmi krátkou oznamovací lhůtu vůči řídicímu orgánu při porušení zabezpečení projektových osobních údajů (24 hodin od zjištění). Před ostrým spuštěním tuto povinnost znovu ověřit v aktuálních pravidlech projektu a určit konkrétní kontaktní osobu.
