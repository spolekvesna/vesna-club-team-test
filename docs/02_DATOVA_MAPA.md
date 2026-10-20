# Datová mapa

## Zdrojový XLSX

### Klienti
`KlientID`, `Kod`, `Jmeno`, `Prijmeni`, `DatumNarozeni`, `DatumVstupu`, `Kontakt`, `OmezenePrilezitosti`, `DokladUlozen`, `Stav`, `Poznamka`.

Mapuje se na `clients`. `KlientID` i `Kod` zůstávají stabilní a unikátní. `DokladUlozen` je tříhodnotové `yes/no/unknown`, aby prázdná hodnota nebyla zaměněna za „ne“.

### Vykony
Zdrojový list má identifikaci klienta, datum, minuty, pracovníka a 10 číselníkových vazeb, ale **nemá KA/podaktivitu**. Importované řádky proto dostanou `ka=legacy`, dokud nejsou ověřené.

Každý nový výkon ukládá i `catalog_snapshot_json`: názvy číselníkových položek tak zůstanou historicky čitelné i po pozdějším přejmenování/sloučení.

### Dokumenty
Ukládají se jako metadata: název, druh, reference/odkaz, datum, pracovník, poznámka. Aplikace není úložiště citlivých skenů.

### DenniZapisy
Jedno datum může mít více záznamů. Každý zápis má vlastní stabilní ID, autora, verzi a audit změn.

### Pracovnici
Email je login identity. Role se mapují na `admin`, `worker`, `reader`; aktivita pracovníka se kontroluje při každém požadavku.

### Ciselniky
Výchozí počet 216 položek:

- Oblast: 14
- Cinnost: 118
- Forma: 7
- Misto: 9
- Metoda: 10
- Jazyk: 6
- Vysledek: 16
- DalsiKrok: 12
- Pokrok: 8
- NavaznaSluzba: 16

Činnosti mohou mít `parent_item_id` na oblast. Použité položky se pouze deaktivují; fyzické smazání je blokováno. Sloučení přesměruje aktivní vazby, ale snapshot výkonu zachová historický název.

## Nové tabulky aplikace

- `events`, `event_workers`, `event_participants` – jedna skupinová akce a více účastníků/pracovníků;
- `indicator_records` – vysvětlitelné zdroje specifických indikátorů;
- `project_outputs` – výstup 028309;
- `web_analytics_aggregates` – výstup 028313;
- `anonymous_feedback_aggregates` – anonymní zpětná vazba oddělená od 026510;
- `audit_log` – kdo/kdy/co změnil;
- `backup_runs` – historie záloh a testů obnovy;
- `import_batches` – náhled a audit řízeného importu.
