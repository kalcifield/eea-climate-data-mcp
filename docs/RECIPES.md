# Investigation recipes

Six reproducible analyses over the EEA GHG inventory and Policies and Measures
(PaMs) databases, run through this tool's CLI. Each recipe records the exact
commands, the aggregation and formula decisions, reference values, and the
caveats that are part of the method — not optional footnotes.

**Reproducibility contract.** All reference values below were retrieved on
**2026-07-19** from `GHG_Inventory.latest` (Hungary submission vintage
`20260315`, inventory years 1985–2024) and `GHGPAMS.latest` (single reporting
round per country, Hungary `Report_ID` 1699). `latest` is mutable: when the
next submission lands, values will shift. Treat the numbers as dated reference
points, not test expectations. Every run prints a `query_hash` and
`retrieved_at` in its provenance block; the hashes below identify the exact
normalized queries used. Units are kt CO₂ equivalent unless noted.

---

## 1. National GHG trend, with and without LULUCF

**Question.** How did a country's total GHG emissions change since 1990, and
how much does LULUCF accounting change the picture?

```bash
uv run eu-climate series emissions --country HU --sector total \
  --accounting-scope without_lulucf --start-year 1990
uv run eu-climate series emissions --country HU --sector total \
  --accounting-scope with_lulucf --start-year 1990
```

**Method.** The helper resolves the plain `Total (with/without LULUCF)`
aggregate-GHG variable and never the `TREND`/`BASE_YEAR_AVG`/`PREV_SUBMISSION`
statistical variants. Percentage change is `(value_end / value_start − 1) × 100`.
Results are sorted client-side (upstream rejects `ORDER BY` on `ghg_value`).

**Reference values (HU, 2026-07-19).**

| Scope | 1990 | 2024 | Change |
| --- | ---: | ---: | ---: |
| without LULUCF | 94 930 | 53 659 | −43.5 % |
| with LULUCF | 91 673 | 47 319 | −48.4 % |

Provenance: `bb16a9be5537…` (without), `d5434f0a28e8…` (with).

**Caveats.** The two scopes are different accounting definitions, not a
data revision; report which one you use. 2024 is the latest published
reporting year, not a real-time figure. The series also extends back to 1985
if you drop `--start-year`.

---

## 2. Sectoral change 1990–2024

**Question.** Which sectors drove the decline, and which resisted it?

```bash
for s in 1 2 3 4 5; do
  uv run eu-climate series emissions --country HU --sector $s --start-year 1990
done
```

**Method.** One series per top-level IPCC sector; each is the reported sector
aggregate (`parameter = 'no parameter'`), never summed from subsectors.
Change is computed per sector; do not sum sector percentages.

**Reference values (HU, 2026-07-19).**

| Sector | 1990 | 2024 | Change |
| --- | ---: | ---: | ---: |
| 1 Energy | 69 480 | 38 040 | −45.3 % |
| 2 Industrial processes | 11 386 | 5 311 | −53.4 % |
| 3 Agriculture | 9 969 | 6 305 | −36.8 % |
| 4 LULUCF (net sink) | −3 257 | −6 340 | sink ×1.9 |
| 5 Waste | 4 095 | 4 003 | −2.2 % |

Provenance: `4233bcf606c6…`, `c189c43efc41…`, `64d31af247af…`,
`a0b53bae583d…`, `c6e34118b42a…`.

**Caveats.** Sector 4 is a net sink; a "+94.7 % change" on a negative number
reads misleadingly — report it as sink deepening. Sector 6 (Other) resolves
but Hungary reports no values under it; an empty series is a correct result.
For this vintage the accounts reconcile exactly: sectors 1+2+3+5 (with 6
empty) sum to the without-LULUCF total, and adding sector 4 yields the
with-LULUCF total. Verify this per country and vintage rather than assuming
it — separate "with indirect CO₂" total variants exist and must not be mixed
into the sum.

---

## 3. Transport growth and the road contribution

**Question.** Transport is the counter-trend sector. How much of its growth
is road transport?

```bash
uv run eu-climate sectors describe 1.A.3
uv run eu-climate series emissions --country HU --sector 1.A.3   --start-year 1990
uv run eu-climate series emissions --country HU --sector 1.A.3.b --start-year 1990
```

**Method.** Compare **deltas**, not shares of levels:
`Δ_sector = value_2024 − value_1990` for `1.A.3` and `1.A.3.b` separately.
The contribution of road to net transport growth is `Δ_road / Δ_transport`.

**Reference values (HU, 2026-07-19).**

| Series | 1990 | 2024 | Δ |
| --- | ---: | ---: | ---: |
| 1.A.3 Transport | 8 936 | 14 016 | +5 080 |
| 1.A.3.b Road transportation | 7 981 | 13 841 | +5 860 |

Road Δ exceeds the whole sector's Δ: the other transport subsectors together
show a net decline, and road explains **more than 100 %** of net transport
growth (+5 860 / +5 080 ≈ 115 %).

Provenance: `57c4fb305bca…` (1.A.3), `8954cb6f6dea…` (1.A.3.b).

**Caveats — double counting is the method here.** Parent sectors already
include their children: sector 1 (38 040) already contains 1.A.3 (14 016);
adding them would invent 52 056 kt that nobody emitted. Never sum a sector
with its parent or children — the helper emits this warning on every
subsector series. A >100 % contribution is arithmetically normal when sibling
subsectors decline; state it explicitly rather than capping at 100 %.

---

## 4. PaMs quantification completeness by country

**Question.** Which countries report structured effect estimates for their
policies and measures, and which report none?

```bash
uv run eu-climate sql run \
  --query-file examples/pams_quantification_completeness.sql \
  --max-rows 40 --page-size 40
```

**Method.** A row counts as ex-ante quantified if **any** of the
`Total_GHG_emissions_reductions_in_{2025,2030,2035}` columns is non-null;
coverage is `max(count_2025, count_2030, count_2035) / n`. Ex-post uses
`Average_expost_emission_reduction`. This is a deliberate definition — the
flat view has 28 ex-ante columns (Total/ESR/EU-ETS/LULUCF × 7 target years);
using only the Total family avoids double-counting split reports.

**Reference values (2026-07-19, selected).**

| Country | Measures | Ex-ante coverage | Ex-post rows |
| --- | ---: | ---: | ---: |
| Norway | 73 | 100 % | 59 |
| Ireland | 96 | 95 % | 42 |
| Germany | 226 | 74 % | 0 |
| **Hungary** | **259** | **0 %** | **0** |

Ten of 30 countries report zero structured quantification (Hungary, Italy,
Denmark, Portugal, Romania, Slovenia, Lithuania, Luxembourg, Cyprus, Malta).
Hungary is the largest all-null portfolio.

Provenance: `4bdd2def65c6…`.

**Caveats.** Null means **not reported**, never zero impact — countries with
0 % coverage may run highly effective measures; the reporting system simply
does not let anyone verify the claimed contribution. Note Germany's pattern:
strong ex-ante, zero ex-post. Explicit reported zeros (e.g. Germany measure
104) count as *reported* and are distinct from null.

---

## 5. Many measures, little quantification, by sector

**Question.** In which policy sectors is the gap between activity (measure
count) and verifiability (quantification) largest, EU-wide?

```bash
uv run eu-climate sql run \
  --query-file examples/pams_sector_quantification.sql \
  --max-rows 500 --page-size 500
```

**Method.** `Sector_s__affected` is multi-valued (`'Transport; Energy
supply'`). Group upstream by the raw string, then split on `;` client-side
and attribute the row's counts to **each** listed sector. A measure listing
two sectors therefore counts once in each — this measures sector exposure,
not a partition; totals across sectors exceed the number of measures by
design.

**Reference values (EU-wide, 2026-07-19, largest sectors).**

| Sector | Measure rows | Quantified (2030) |
| --- | ---: | ---: |
| Energy consumption | 1 207 | 22 % |
| Energy supply | 1 162 | 10 % |
| Transport | 883 | 18 % |
| Agriculture | 433 | 24 % |

Provenance: `30dde2a33ecd…`.

**Caveats.** Quantified here = non-null `Total_..._in_2030` only (single-year
proxy, stricter than recipe 4's any-of-three definition — state which one you
use). The "unspecified" sector bucket has the *highest* quantification rate
(44 %), which says more about who fills forms carefully than about sectors.

---

## 6. Emissions trend × reported measure stock

**Question.** What does a country's actual emissions trend look like next to
the policy portfolio it reports for the same sector?

```bash
uv run eu-climate series emissions --country HU --sector 1.A.3 --start-year 1990
uv run eu-climate sql run --query-file examples/hu_transport_measures_by_status.sql \
  --max-rows 10 --page-size 10
uv run eu-climate sql run --query-file examples/hu_measures_by_status.sql \
  --max-rows 10 --page-size 10
```

**Method.** Join by narrative, not by key: the inventory and PaMs databases
share no join column, and sector taxonomies differ (IPCC codes vs PaMs sector
labels). Pair one sector series with the measure counts whose
`Sector_s__affected` contains the matching label, and keep the two provenance
blocks separate.

**Reference values (HU, 2026-07-19).** Transport emissions grew +57 % since
1990 (recipe 3) while Hungary reports 29 *Implemented*, 2 *Planned* and 6
*Expired* transport measures — none with a structured effect value (recipe
4). Portfolio-wide: 180 Implemented, 38 Expired, 37 Planned, 4 Adopted.

Provenance: `57c4fb305bca…` (series), `6bda4fb36e9d…` (transport measures),
`a143edc686c2…` (all statuses).

**Caveats.** The safe claim is precisely bounded: *rising sector emissions
coexist with a reported measure stock whose contribution cannot be verified
from the official reporting system*. This does **not** show the measures are
ineffective, and "most measures of any sector" claims require comparing all
sectors first. The 92 % EU-policy-linked share of Hungary's portfolio is a
reported flag, not evidence about motivation or origin.
