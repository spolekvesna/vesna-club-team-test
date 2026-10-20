# Ostrá migrace a přepnutí

## Zásada

Dodaný XLSX je snapshot. Před ostrým startem se musí porovnat s **aktuálním živým Google sešitem**, jak požaduje zadání.

## Postup

1. domluvit krátké „freeze“ období, kdy se stará evidence už nebude měnit;
2. exportovat živý Google sešit do XLSX;
3. v aplikaci `Import` nahrát soubor pouze do náhledu;
4. zkontrolovat hlavičky, počty řádků a varování;
5. pokud jsou v `Vykony` řádky bez KA, rozhodnout jejich mapování před vykazováním;
6. spustit databázovou zálohu prázdné/počáteční produkce;
7. potvrdit import;
8. porovnat počty klientů, pracovníků, výkonů, dokumentů, denních zápisů a číselníků;
9. ručně zkontrolovat náhodný vzorek klientských karet proti zdroji;
10. zkontrolovat indikátory a jejich zdrojové záznamy proti papírovým listinám;
11. starý sešit převést do read-only archivu, aby nevznikly dvě paralelní pravdy.

## Rollback

Pokud se po importu zjistí zásadní chyba:

- nepokračovat v nové evidenci;
- zaznamenat důvod;
- obnovit produkční DB z předimportní zálohy;
- opravit mapování/import;
- import zopakovat z téhož zmrazeného zdroje.

Import je idempotentní podle stabilních ID, ale rollback přes databázovou zálohu je bezpečnější než „ruční odmazávání“ importovaných řádků.
