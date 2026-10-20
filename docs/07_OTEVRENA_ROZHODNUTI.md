# Otevřená rozhodnutí před produkcí

Aplikace je na těchto místech úmyslně konzervativní; nemá si vymýšlet projektovou metodiku.

1. **Historické Vykony bez KA** – určit mapování starých řádků, pokud v živém sešitu skutečně existují. Do té doby `legacy` a kontrolní varování.
2. **KA3.1 + 3.2 limit 10 h** – potvrdit, zda 10 h znamená společný limit pro obě podaktivity na osobu, nebo jiný metodický výklad. Teď je to pouze konfigurovatelné upozornění.
3. **026510** – potvrdit schválenou metodiku a vztah k anonymnímu 70% cíli. Aplikace jej do té doby automaticky nepočítá.
4. **Retence** – potvrdit dobu uchování živých dat, auditů, importů a záloh.
5. **Dokumentové odkazy** – definovat přesnou strukturu omezeného Google Drive a kdo smí odkazy otevírat.
6. **Reader role** – potvrdit, zda interní kódy osob ve zdrojových reportech stačí, nebo má být role ještě více agregovaná.
7. **Hosting sizing** – nejmenší placená DB 256 MB je rozumný start pro malou evidenci; po pilotu sledovat RAM/CPU a podle potřeby zvýšit plán.
