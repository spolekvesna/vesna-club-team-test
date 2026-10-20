# Postup při bezpečnostním incidentu

## Okamžitě

1. incident nebagatelizovat ani nemažte stopy;
2. zaznamenat datum/čas zjištění, oznamovatele, dotčený systém a první známé skutečnosti;
3. omezit další únik/zneužití (deaktivace účtu, rotace klíče, izolace služby) tak, aby se pokud možno zachovaly důkazy;
4. informovat určenou odpovědnou osobu Vesny;
5. zjistit, zda jsou dotčena skutečná osobní data a jakého rozsahu.

## Oznámení

GDPR: podle aktuálních informací ÚOOÚ správce oznamuje rizikové porušení Úřadu bez zbytečného odkladu a pokud možno do 72 hodin od okamžiku, kdy se o něm dozvěděl; nerizikové incidenty se neposílají automaticky, ale riziko se musí posoudit a incident dokumentovat.

Oficiální informace: https://uoou.gov.cz/profesional/poruseni-zabezpeceni-osobnich-udaju

Projekt: zadání uvádí, že přiložená PZP vyžadují u projektových osobních údajů informování řídicího orgánu do 24 hodin od zjištění. Tuto povinnost a kontaktní cestu před produkcí znovu ověřit v aktuálních pravidlech projektu. Kratší projektovou lhůtu řešit nezávisle na 72hodinové GDPR lhůtě.

## Co shromáždit

- čas vzniku/zjištění/ukončení;
- systémy, účty a kategorie dat;
- odhad počtu osob a záznamů;
- pravděpodobné důsledky;
- přijatá a plánovaná opatření;
- logy/audit/hosting události;
- informace od zpracovatelů;
- rozhodnutí, zda a proč se oznamuje/neoznamuje ÚOOÚ a dotčeným osobám.

## Po incidentu

- změnit kompromitované přístupy;
- ověřit integritu DB a posledních záloh;
- provést restore test;
- doplnit kořenovou příčinu a nápravná opatření;
- zkontrolovat, zda se má upravit interní směrnice, role, retence nebo dodavatelská konfigurace.
