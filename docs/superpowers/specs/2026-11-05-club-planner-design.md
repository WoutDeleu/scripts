# Badminton Club Tournament Planner Design

## Context and verified source behavior

The target tournament is `046F75E1-3C36-4755-BD5E-C6488E44DE36` on
Badminton Vlaanderen's Tournamentsoftware site. Live checks on 5 November 2026
found:

- The overview lists 25 events, 325 entries, 324 players, and the tournament
  dates and venue.
- The tournament player page is an HTML shell. Its observed POST form action,
  `/Players/GetPlayersContent`, returns player IDs and affiliations.
- Event detail pages contain accepted/alternate entry lists, player links, and
  doubles/mixed pairings.
- The draw index lists knockout and group draw structures. Draw 26's observed
  `GetDrawContent` and `GetMatchesContent` requests provide round structure,
  entrants, clubs, byes, match IDs, and results. Draw 5's observed
  `GetMatchesContent` contains round-robin matches.
- Both tournament-day match pages return the explicit empty-state text
  “Geen wedstrijden gevonden”; draw match lists say “nog niet gepland.”
  Draws are therefore published, but no scheduled matches or times were
  published at retrieval time.
- The sampled group draw has no visible playoff qualification mapping.
  Progression beyond that group stage must be marked unresolved.
- Player affiliations use `PLUIMPLUKKERS BC`; the club directory has one
  matching club, `BC Pluimplukkers`, with directory ID
  `13F15128-64AB-409A-8F9D-750C12961AA3`. The tool must disclose this unique
  canonical-name resolution rather than silently treating names as identical.
- The club directory's observed search form posts to `/find/club/DoSearch`;
  use it to obtain a stable club ID when the requested name and tournament
  affiliation label differ.

The source has no generally documented public API. The observed HTTP pages and
their own form/script-requested content endpoints are sufficient for the
verified structures; browser execution is not currently justified.

## Goals and non-goals

The tool accepts a tournament URL and club name and creates an English `.xlsx`
workbook containing the club overview, one sheet per selected player, and
information/legend. It includes published entries and partners even before
matches are scheduled, and adds only future matches and paths derivable from
source-backed bracket/group relationships. It is an extractor and planner,
not a scheduler, prediction model, or qualification-rule guesser.

The implementation must distinguish empty published content from HTTP errors,
login/cookie pages, unsupported markup, and empty application shells. Any
uncertain relationship is surfaced as unresolved. It must not bypass access
controls or use authentication credentials.

## Architecture

Keep the implementation as a small importable Python package with separable
responsibilities:

- **Retrieval:** A single HTTP session follows links observed in the source,
  including the player-list POST and draw content requests. Set explicit
  timeouts, bounded retries for transient failures, a conservative per-host
  request interval, and per-invocation caching only. Do not silently use stale
  persistent responses.
- **Parsing and identity:** Parse tournament metadata, events, player IDs,
  affiliations, entry states, pairs, draw/group contents, matches, scores,
  dates, and source URLs. Resolve the requested club using exact normalized
  names first; permit a unique canonical/affiliation alias only when the
  source provides one unambiguous candidate, and record the selected source
  name and ID in warnings/metadata. Query the observed club directory search
  form for the canonical club ID when necessary; map affiliation labels to
  directory names only when the relationship is unique. Fail clearly on
  ambiguity or missing affiliation. Keep source IDs as identities.
- **Progression:** Represent source matches and feeder relationships explicitly.
  Derive knockout progression from the observed bracket structure and published
  results, excluding byes from win counts and not creating bye match rows.
  Represent group matches separately; only connect them to playoffs when the
  source publishes qualification rules and feeders. Preserve alternative paths
  and participant-level conditions. Mark unsupported or unmapped paths
  unresolved.
- **Workbook and CLI:** Generate the overview, player sheets, and information/
  legend with openpyxl. Keep status text separate from win-depth colors, use
  dates/times as Excel values, write source text as literal cell content, and
  include links, extraction status, warnings, timezone availability, and
  retrieval time. Save to a temporary file beside the requested destination
  and atomically replace it only after successful workbook validation.

The proposed package separates `source`, `models`/identity, `progression`,
`workbook`, and CLI entry points. It will add only the HTTP/HTML and Excel
dependencies needed by this project and preserve existing scripts.

## Workbook behavior

The workbook uses English headings and source names unchanged. The club
overview has one row per actual or source-backed future match, with player
participation and conditions represented individually when paths converge.
Player sheets list entries/partners and all relevant actual or reachable future
matches. Dated matches sort chronologically; undated/unscheduled items are
clearly separated and no timestamps are fabricated.

Additional-wins colors count wins needed to enter a future match. Current
matches are unfilled; increasing win depths use distinct fills and are also
printed textually. Group qualification conditions are not translated into
invented win counts. A legend explains statuses, colors, source provenance,
publication state, and extraction limitations. Sheet names are sanitized and
unique; text beginning with formula characters is stored as literal content.

When draws are absent but entries are available, produce an entries-only
workbook and explicitly state the publication status. A successful empty match
list is not a failure. If an optional page/request fails after the core
tournament, roster, and entries are known, produce a clearly marked PARTIAL
workbook containing the successful data, include the failed section and error
as a warning, and exit nonzero. Never convert such failures into “not
published.” If the tournament identity, club identity, core roster, or workbook
cannot be validated, fail without replacing an existing output file.

## Validation

Use deterministic HTML/model fixtures and workbook inspection tests. Cover
identity resolution and ambiguity, missing affiliations, duplicate player
names with different IDs, mixed-club pairs, club-versus-club matches, match
deduplication, knockout progression/byes/results/walkovers, group qualification
and unresolved paths, alternative opponents, absent draw/time states, request
and parse failures, literal cell text, sheet names, hyperlinks, dates, status
text, and actual fill colors.

Live verification on the target will check a knockout entrant, a doubles or
mixed pair with a selected-club player, a potential later-round opponent, and
the current schedule publication state. Group-to-playoff behavior not available
from the target will be tested using a deterministic fixture and described as
fixture-verified, not target-verified. Generate and inspect the target workbook
before claiming completion.

## Known limitations

There is no documented general public API. Parsing relies on the live HTML and
observed Tournamentsoftware content requests, which may change; unsupported
structures must fail explicitly. The target currently has no scheduled match
times. The sampled group draw has no published playoff mapping, so the workbook
must stop that progression visibly rather than infer it.
