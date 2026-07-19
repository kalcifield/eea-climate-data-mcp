# SPIKE — hun-climate-policy-mcp

> Historical brief: this Hungary-focused spike led to the first vertical slice. The
> maintained product is now country-neutral and named `eea-climate-data-mcp`; current
> behavior and evidence are documented in `README.md` and `SPIKE-REVIEW.md`.

## Cél

Vizsgáld meg, hogy az EEA Discodata publikus query API-jára építve létrehozható-e egy megbízható, agent-barát CLI + MCP szolgáltatás magyar klímavédelmi adatok vizsgálatához.

A fő kérdés:

> Lehet-e az EEA hivatalos, tagállami jelentésekből származó adatait schema-aware, read-only SQL felülettel elérhetővé tenni úgy, hogy az agent kevés próbálkozással tudjon valódi klímapolitikai vizsgálatokat végezni?

A projekt ne puszta HTTP-wrapper legyen. A hozzáadott érték:

- adatbázis- és sémakeresés;
- grain-, join- és kódlista-információ;
- validált read-only SQL;
- kompakt, lapozható eredmény;
- provenance;
- a tényleges, becsült és tervezett adatok világos elkülönítése.

## Projektazonosítók

- Repository: `hun-climate-policy-mcp`
- Python package: `hun_climate_policy`
- CLI: `hun-climate`
- MCP server: `hun-climate-policy-mcp`

## Elsődleges adatforrás

### EEA Discodata

Ellenőrizendő:

- publikus hozzáférés és autentikáció;
- adatbázis- és verzióstruktúra;
- query endpoint és támogatott SQL-részhalmaz;
- lapozás, timeout és maximális oldalméret;
- stabil rendezés és eredményismétlődés;
- hibatípusok és szolgáltatási feltételek;
- provenance és verziókövetés.

## Milyen kérdéseket kell tudnia megválaszolni?

### Tényleges kibocsátások

- Hogyan változott Magyarország teljes ÜHG-kibocsátása 1990 óta?
- Mely ágazatok csökkentették vagy növelték leginkább a kibocsátásukat?
- Mennyi a kibocsátás LULUCF-fel és anélkül?
- Hogyan viszonyul Magyarország más uniós országokhoz?

### Klímapolitikai intézkedések

- Milyen magyar klímapolitikai intézkedéseket jelentettek?
- Melyek végrehajtottak, elfogadottak vagy tervezettek?
- Mely ágazatokat célozzák?
- Mekkora kibocsátáscsökkentést várnak tőlük?
- Mely intézkedésekhez van ex post értékelés?

### Projekciók és célpályák

- Mi a különbség a WEM és WAM forgatókönyv között?
- Elégséges-e a jelenlegi intézkedéscsomag a 2030-as célhoz?
- Hol tér el a tényleges trend a korábban jelentett projekciótól?
- Mely ágazatokban marad a legnagyobb kibocsátás 2030 után?

## Megbízhatósági modell

A SPIKE dokumentálja:

- a tagállami jelentési kötelezettséget;
- az EU Governance Regulation kapcsolatát;
- az UNFCCC és IPCC módszertani keretet;
- az EEA QA/QC folyamatát;
- a verziózott jelentési ciklusokat.

A tool minden eredményben különböztesse meg:

```text
reported_actual
reported_projection
reported_policy_estimate
derived_by_tool
```

## Mielőtt bármit implementálsz

- Olvasd el a repository és agent instrukciókat.
- Ellenőrizd a live Discodata dokumentációt és API-t.
- Térképezd fel a releváns adatbázisokat, verziókat és táblákat.
- Azonosítsd a magyar rekordok szűrésének módját.
- Ellenőrizd a grain-t, kulcsokat, kódlistákat és joinokat.
- Először készíts önálló review-t és GO / CONDITIONAL GO / NO-GO javaslatot.
- Csak akkor implementálj, ha világos a stabil MVP-határ.

## Raw SQL stratégia

A raw SQL legyen engedélyezett. Az agentek jól tudnak SQL-t írni, ha elegendő kontextust kapnak.

A kívánt workflow:

```text
list databases
→ inspect version
→ describe table
→ inspect relationships and code lists
→ preview rows
→ validate/explain SQL
→ execute bounded SQL
→ return provenance
```

## Javasolt MCP tool surface

### Discovery

```text
list_databases
list_versions
list_tables
search_tables
describe_table
describe_relationships
find_columns
list_distinct_values
preview_rows
```

### SQL

```text
get_sql_capabilities
validate_sql
explain_sql
query_sql
```

### Provenance

```text
get_provenance
describe_reporting_status
```

### Opcionális high-level toolok

Csak akkor, ha a review igazolja:

```text
search_climate_measures
compare_scenarios
assess_target_progress
```

## Javasolt CLI

```bash
hun-climate databases list
hun-climate tables search "policy measure"
hun-climate tables describe --database <db> --version <version> --table <table>
hun-climate values distinct --database <db> --version <version> --table <table> --column CountryCode
hun-climate sql validate --query-file query.sql
hun-climate sql explain --query-file query.sql
hun-climate sql run --query-file query.sql --format json --max-rows 500
```

Minden adatparancs támogassa:

```text
--format json
--format jsonl
--max-rows
--page
--page-size
--timeout
--no-cache
--explain
```

## SQL capability SPIKE

Empirikusan teszteld:

- `SELECT`, `WHERE`, `JOIN`;
- `GROUP BY`, `HAVING`, `ORDER BY`;
- `DISTINCT`, `TOP`, `CASE`;
- `IN`, `LIKE`, `BETWEEN`;
- aggregációk és scalar függvények;
- derived table és nested subquery;
- correlated subquery;
- `UNION` / `UNION ALL`;
- window functions;
- `STRING_AGG`, `PIVOT`;
- cross-database join;
- CTE / `WITH`;
- multiple statements;
- alias-követelmény;
- dátumkonverzió és null-kezelés.

A capability tool adjon géppel olvasható mátrixot.

## SQL guardrails

`query_sql` előtt kötelező validáció:

- csak egy statement;
- csak `SELECT`;
- író és DDL kulcsszavak tiltása;
- `EXEC`, stored procedure és `SELECT INTO` tiltása;
- system schema tiltása;
- allowlistelt adatbázisok és verziók;
- kötelező row limit;
- maximális timeout és page size;
- determinisztikus `ORDER BY` javaslat lapozásnál;
- alias ellenőrzés computed column esetén;
- query logging és cancellation support.

Lehetőleg SQL parser-t használj, ne csak regexet.

## `explain_sql`

Legalább ezt adja vissza:

- érintett adatbázisok, verziók, táblák és oszlopok;
- joinok és aggregációk;
- szűrők és limitek;
- potenciális grain mismatch;
- duplikációs kockázat;
- nem determinisztikus lapozás;
- tiltott vagy nem támogatott konstrukció;
- provenance impact.

## Sémakontextus

A `describe_table` tartalmazza:

- table description;
- grain;
- logical key;
- reporting cycle;
- oszlopok, típusok és egységek;
- kódlisták és minták;
- null semantics;
- joinok;
- caveatok;
- forrásdokumentumok.

## Elsődleges adatköri jelöltek

A live neveket és verziókat a SPIKE azonosítsa.

Elsőként vizsgálandó:

1. Greenhouse gas inventory
2. Policies and Measures
3. GHG projections
4. Target progress
5. EU ETS, ha ugyanazon szolgáltatáson értelmesen elérhető

## Magyar fókusz

Ellenőrizd:

- milyen country code jelöli Magyarországot;
- következetes-e a kód az adatbázisok között;
- mennyire teljesek a magyar policy rekordok;
- mennyi ex ante és ex post számszerű hatás található;
- milyen reporting year-ek vannak;
- hogyan kapcsolhatók össze a projekciók és intézkedések;
- mennyire stabilak a rekordok verziók között.

## Elsődleges agent use case-ek

### Tényleges trend

> Hogyan változott Magyarország ágazati ÜHG-kibocsátása 1990 óta?

### Intézkedések rangsorolása

> Mely végrehajtott magyar intézkedésekhez jelentették a legnagyobb 2030-as kibocsátáscsökkentést?

### WEM vs WAM

> Mekkora különbséget jelent a jelenlegi és további intézkedések forgatókönyve 2030-ban?

### Célpálya

> Összhangban van-e a tényleges trend és a WEM projekció a 2030-as magyar céllal?

## Nem cél

- általános EEA adatplatform;
- minden Discodata adatbázis támogatása;
- klímapolitikai oksági következtetés;
- települési vagy vállalati kibocsátás kitalálása;
- teljes dashboard-rendszer;
- saját adattár építése, ha az upstream query elegendő;
- validáció nélküli szabad SQL továbbítása.

## Technikai architektúra

```text
hun_climate_policy/
├── domain/
├── application/
│   ├── discovery.py
│   ├── schema.py
│   ├── sql_validation.py
│   └── query.py
├── providers/
│   └── discodata.py
├── infrastructure/
│   ├── http.py
│   ├── cache.py
│   └── config.py
├── adapters/
│   ├── cli.py
│   └── mcp.py
└── profiles/
    └── hungary_climate.py
```

A CLI és MCP ugyanazt az application logikát használja.

## Ajánlott Python stack

- Python 3.11+
- `httpx`
- `pydantic`
- `typer`
- official MCP Python SDK
- T-SQL-képes SQL parser
- `platformdirs`
- SQLite vagy `diskcache`
- `pytest`
- `respx`
- recorded fixtures

## Cache hipotézis

- adatbázislista: 24 óra;
- verziólista: 24 óra;
- table schema: 24 óra;
- distinct values: 6–24 óra;
- query result: rövid vagy query-hash alapján;
- hibák: ne cache-eld, vagy csak rövid ideig.

## Pagination és stabilitás

Teszteld:

- ismétlődő és hiányzó rekordok lapozáskor;
- `ORDER BY` nélküli query;
- stabil unique key;
- maximum page size;
- duplicate detection.

Figyelmeztetés:

```text
pagination requested without deterministic ORDER BY
```

## Provenance

Minden query eredménye tartalmazza:

```json
{
  "provider": "EEA Discodata",
  "database": "...",
  "version": "...",
  "tables": ["..."],
  "query_hash": "...",
  "retrieved_at": "...",
  "reporting_status": "reported_actual",
  "source_links": ["..."],
  "warnings": []
}
```

## Tesztelés

### Unit

- SQL classification;
- tiltott statement detektálás;
- CTE detektálás;
- row-limit injection;
- alias validation;
- table allowlist;
- provenance;
- reporting status mapping.

### Contract

- recorded Discodata responses;
- database és schema discovery;
- pagination;
- invalid és unsupported SQL;
- timeout;
- empty/partial result;
- schema drift.

### Live smoke

- database list;
- egy table description;
- egy distinct-value query;
- egy kis Hungary-filtered query;
- egy grouped aggregation;
- egy paginated query;
- nincs load test.

### Adapter equivalence

A CLI és MCP:

- ugyanazt az application service-t hívja;
- szemantikailag azonos eredményt ad;
- azonos provenance mezőket és guardrailokat használ.

## SPIKE kimenete

1. Review findings.
2. GO / CONDITIONAL GO / NO-GO döntés.
3. Live Discodata capability matrix.
4. Releváns adatbázisok és verziók.
5. Magyar adatok teljességének értékelése.
6. Sémák, grain-ek és joinok dokumentációja.
7. SQL guardrail terv.
8. Javasolt MCP tool surface.
9. Javasolt CLI felület.
10. Minta SQL és JSON válaszok.
11. Kockázatlista.
12. Következő MVP scope.
13. Pontos teszt- és live proof eredmények.

## GO kritériumok

GO, ha:

- a publikus query hozzáférés stabil;
- a magyar rekordok következetesen szűrhetők;
- inventory, PaM és projection adatok elérhetők;
- a sémák programozottan felderíthetők;
- a joinok dokumentálhatók;
- a raw SQL biztonságosan korlátozható;
- tipikus kérdések 2–5 hívással megoldhatók;
- az eredmény többet ad az EEA dashboardjánál;
- a provenance és reporting status egyértelmű.

## CONDITIONAL GO

Ha az adat jó, de a schema metadata gyenge, a policy rekordok hiányosak vagy a szolgáltatás instabil, a projekt lehet:

```text
discodata-mcp + Hungary climate profile
```

## NO-GO jelek

- a magyar rekordok nem következetesen szűrhetők;
- nincs elég számszerű policy/projection adat;
- a sémák túl instabilak;
- a query endpoint túl korlátozott;
- a használati élmény nem jobb a fájlletöltésnél vagy dashboardnál;
- a provenance nem rekonstruálható;
- az agent túl sok trial-and-error lépésre kényszerül.

## Első implementálható vertical slice

Csak akkor készítsd el, ha a review indokolja:

```text
list databases
→ describe one climate table
→ validate read-only SQL
→ run bounded Hungary-filtered aggregation
→ compact JSON
→ provenance
→ CLI és MCP ugyanazon application logikán
```

Ehhez elegendő:

- egy Discodata provider;
- schema és provenance modellek;
- SQL validator;
- `list_databases`;
- `describe_table`;
- `query_sql`;
- egy CLI command group;
- három MCP tool;
- recorded fixture;
- unit és contract tesztek;
- live smoke script.

## Műveleti korlát

Ne pusholj, ne merge-ölj, ne nyiss vagy zárj issue-t/PR-t, ne címkézz, és ne írj nyilvános kommentet külön utasítás nélkül.
