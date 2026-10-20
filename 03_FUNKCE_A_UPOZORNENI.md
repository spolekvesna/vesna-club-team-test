# Vesna Club TEAM TEST – funkce a upozornění

## Co je určeno k reálnému otestování

- víceuživatelská práce nad jednou databází;
- klientské karty a úplná historie evidence;
- individuální výkony;
- KA1, KA2, KA3.1, KA3.2 a KA3.3;
- skupinové akce s více účastníky;
- denní zápisy a jejich historie;
- pracovníci a role;
- všechny číselníky spravované přímo v aplikaci;
- indikátory a jejich elektronické zdroje;
- kontrolní výstupy a exporty;
- současná editace stejného záznamu;
- responzivní zobrazení.

## Bezpečnost TEAM TESTU

TEAM TEST používá syntetická data a lokální testovací přihlášení. Není určen pro skutečné klientské údaje. Produkční bezpečnostní vrstva bude navíc používat Google Workspace Vesny, produkční databázi, provozní zálohy, restore test a dokončený GDPR/provozní režim.

## Free Render není produkce

- web se po 15 minutách nečinnosti uspí;
- probuzení může trvat přibližně minutu;
- Free PostgreSQL expiruje po 30 dnech;
- Free PostgreSQL nemá databázové zálohy;
- testovací data jsou dočasná.

## Historie číselníků

Použité položky číselníku se nesmějí z historie „ztratit“. Systém proto drží identifikátor i historický název použitý při zápisu. Pozdější přejmenování či deaktivace nemá přepsat význam starého výkonu.

## KA3 limity

Limity v KA3 jsou nyní nastavené jako upozornění. Uživatel může záznam uložit i po dosažení limitu; systém má na situaci upozornit. Před produkcí lze pravidla upravit podle definitivní metodiky.

## Indikátory

Unikátní osoba se nemá u stejného indikátoru započítat vícekrát jen proto, že byla v několika aktivitách. U vypočteného čísla má být možné dohledat elektronické zdrojové záznamy pro kontrolu proti papírové evidenci.

## Dokumenty

TEAM TEST nepoužívá aplikaci jako úložiště citlivých klientských dokumentů. Evidence pracuje s metadaty a odkazem na řízené úložiště. Před produkcí se nastaví konečný režim Google Drive/oprávnění.

## Reader / reporting

Role čtenáře je úmyslně omezená. Nemá být „levnější pracovník“, ale role pro agregované reportování bez klientských detailů.

## Zálohy

Produkční aplikace má připravený režim automatické databázové zálohy a restore testu. V bezplatném TEAM TESTU tato část není produkčně provozovaná; cílem TEAM TESTU je ověřit logiku a použitelnost aplikace.
