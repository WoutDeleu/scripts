# Badminton Club Tournament Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable Python CLI that retrieves published badminton tournament data and generates a club-wide Excel planning workbook without inventing match facts or progression.

**Architecture:** Use a requests session to retrieve pages and observed content endpoints, BeautifulSoup parsers to build stable-ID domain records, isolated identity and progression functions, and openpyxl for the workbook. The CLI orchestrates these components and only atomically replaces the requested output after a complete, validated run.

**Tech Stack:** Python 3.12, requests, beautifulsoup4, openpyxl, pytest.

**Spec:** `docs/superpowers/specs/2026-11-05-club-planner-design.md`

## Global Constraints

- Preserve published player and event names; use English headings, conditions, and explanations.
- Use stable source IDs as identities, not names alone.
- Do not infer draw connections from similar names, chronological ordering, or guessed match-number arithmetic.
- Do not create a scheduled-match row for a bye; byes do not count as wins.
- Only connect group qualification to playoffs when the source publishes the rules and feeder links; otherwise mark progression unresolved.
- Distinguish an empty published page from request failures, login/cookie pages, empty application shells, and unsupported structures.
- Use explicit timeouts, bounded retries, a conservative request interval, and per-invocation caching; never silently use stale data.
- Write website-derived text as literal Excel cell content.
- Save beside the target and atomically replace it only after successful workbook validation; clearly mark valid partial data and return a nonzero status.
- The target currently has published draws but no scheduled match times; describe it as live-verified only to that extent.

---

## File Structure

- Create `club_planner/__init__.py` to expose the package version.
- Create `club_planner/__main__.py` to run the module CLI.
- Create `club_planner/models.py` for immutable player, event, entry, entrant, draw, match, tournament, and progression records.
- Create `club_planner/http_client.py` for session reuse, request throttling, retry policy, and in-run response caching.
- Create `club_planner/parsing.py` for source-page validation and HTML-to-model parsing, including the observed club directory search response.
- Create `club_planner/identity.py` for exact and unique club identity resolution.
- Create `club_planner/progression.py` for feeder paths, reachability, conditions, and additional-win depth.
- Create `club_planner/workbook.py` for workbook sheets, formulas-as-literal protection, formatting, and atomic writing.
- Create `club_planner/cli.py` for argument parsing and end-to-end orchestration.
- Create `tests/conftest.py` and synthetic HTML fixtures under `tests/fixtures/`.
- Create `tests/test_identity.py`, `tests/test_parsing.py`, `tests/test_http_client.py`, `tests/test_progression.py`, `tests/test_workbook.py`, and `tests/test_cli.py`.
- Modify `requirements.txt` to add only requests, beautifulsoup4, and openpyxl.
- Modify `README.md` with installation, CLI use, source behavior, and limitations.
- Generate `planning.xlsx` for the target after implementation and manually inspect the workbook.

## Task 1: Domain records and unambiguous club resolution

**Files:**
- Create: `club_planner/__init__.py`
- Create: `club_planner/models.py`
- Create: `club_planner/identity.py`
- Test: `tests/test_identity.py`

**Interfaces:**
- `Player(id: str, name: str, affiliation: str | None, profile_url: str | None)`
- `Club(id: str | None, name: str, affiliation_names: tuple[str, ...])`
- `TournamentMetadata(title: str, url: str, start_date: date | None, end_date: date | None, venue: str | None, timezone_label: str | None)`
- `Event(id: str, name: str, url: str)`
- `Draw(id: str, event_id: str, name: str, kind: str, url: str, content_url: str | None, matches_url: str | None)`
- `Entry(id: str, event_id: str, player_ids: tuple[str, ...], status: str, source_url: str)`
- `Entrant(id: str, player_ids: tuple[str, ...], label: str, club_names: tuple[str | None, ...], source_url: str | None, placeholder: str | None)`
- `Match(id: str, source_id: str | None, event_id: str, draw_id: str | None, round_name: str, side_a: Entrant | None, side_b: Entrant | None, feeder_ids: tuple[str, ...], status: str, winner_player_ids: tuple[str, ...], score: str | None, match_date: date | None, start_time: time | None, venue: str | None, court: str | None, source_url: str | None)`
- `PublicationState` has `PUBLISHED`, `PUBLISHED_EMPTY`, `NOT_PUBLISHED`, and `UNKNOWN`; `UNKNOWN` is never rendered as an established unpublished state.
- `TournamentData` contains `TournamentMetadata`, retrieval timestamp, players, clubs, events, draws, entries, matches, publication states, and warnings as immutable tuples, plus an explicit partial-extraction flag.
- `Participation` contains `player_id`, `match_id`, `conditions: tuple[str, ...]`, `additional_wins: int | None`, `knockout_wins_after_qualification: int | None`, `qualification_text: str | None`, and `unresolved: bool`.
- `ProgressionResult(matches: tuple[Match, ...], participations: tuple[Participation, ...], warnings: tuple[str, ...])`.
- `normalize_name(value: str) -> str` case-folds and collapses whitespace.
- `resolve_club(requested: str, candidates: tuple[Club, ...]) -> tuple[Club, str | None]` returns the uniquely resolved club and an optional disclosure warning; it raises a specific ambiguity or no-match exception rather than selecting arbitrarily.

- [ ] **Step 1: Write failing identity tests**

Add tests for case/whitespace-insensitive exact matching, canonical name versus affiliation alias, the unique “Pluimplukkers” to “BC Pluimplukkers” mapping, ambiguity when two candidates share the query, missing affiliation, and two same-name players with different IDs.

```python
def test_unique_club_alias_is_reported():
    club = Club("13F15128-64AB-409A-8F9D-750C12961AA3",
                "BC Pluimplukkers", ("PLUIMPLUKKERS BC",))
    resolved, warning = resolve_club("Pluimplukkers", (club,))
    assert resolved.id == club.id
    assert warning is not None
```

Define `knockout_matches` in `tests/test_progression.py` as `qf1` (p1 versus p2), `qf2` (p3 versus p4), `semi` (winners of qf1/qf2), `semi_other` (a source-backed pair of unresolved quarterfinal winners), and `final` (winners of semi/semi_other). With qf1 unplayed, p1 needs one win to enter semi and two to enter final. Add a separate case where p1 is listed against a bye and enters the next round with zero additional wins.

- [ ] **Step 2: Run the identity tests and confirm they fail**

Run: `python -m pytest -q tests/test_identity.py`
Expected: collection fails because the package and resolver do not exist.

- [ ] **Step 3: Implement typed immutable records and deterministic resolution**

Implement the interfaces above with frozen dataclasses. Compare normalized full names and source-provided aliases first. If exact matching fails, allow a candidate only when the requested normalized words identify exactly one known candidate; return a warning describing the canonical name and source affiliation. Raise `ClubResolutionError` with candidate names for zero or multiple matches.

- [ ] **Step 4: Run identity tests**

Run: `python -m pytest -q tests/test_identity.py`
Expected: every exact, alias, ambiguity, unavailable-affiliation, and same-name/different-ID test passes.

- [ ] **Step 5: Commit the domain and identity layer**

```bash
git add club_planner/__init__.py club_planner/models.py club_planner/identity.py tests/test_identity.py
git commit -m "feat: add planner domain and club resolution"
```

## Task 2: Responsible retrieval and source parsing

**Files:**
- Create: `club_planner/http_client.py`
- Create: `club_planner/parsing.py`
- Create: `tests/test_http_client.py`
- Create: `tests/test_parsing.py`
- Create: `tests/fixtures/overview.html`
- Create: `tests/fixtures/players-shell.html`
- Create: `tests/fixtures/players-content.html`
- Create: `tests/fixtures/event-doubles.html`
- Create: `tests/fixtures/knockout-content.html`
- Create: `tests/fixtures/group-content.html`
- Create: `tests/fixtures/empty-schedule.html`

**Interfaces:**
- `HttpClient(timeout: tuple[float, float] = (5.0, 20.0), min_interval: float = 1.0, retries: int = 2)`.
- `HttpClient.get(url: str) -> Response` and `HttpClient.post(url: str, data: dict[str, str] | None = None) -> Response` use one session, bounded transient retries, host-level pacing, and an in-memory cache keyed by method, URL, and submitted data.
- `parse_tournament_overview(html: str, source_url: str) -> TournamentMetadata`.
- `parse_events(html: str, source_url: str) -> tuple[Event, ...]`.
- `parse_players(html: str, source_url: str) -> tuple[Player, ...]`.
- `parse_club_directory(html: str, source_url: str) -> tuple[Club, ...]`.
- `parse_entries(html: str, event: Event) -> tuple[Entry, ...]`.
- `parse_draw_index(html: str, source_url: str) -> tuple[Draw, ...]`.
- `parse_draw_content(html: str, draw: Draw, source_url: str) -> tuple[Match, ...]`.
- `parse_match_list(html: str, source_url: str) -> tuple[Match, ...]`.
- `classify_page(html: str, expected_markers: tuple[str, ...]) -> PublicationState` returns published, published-empty, not-published only for an explicit source marker, or unknown; it raises a typed `RetrievalError`/`UnsupportedPageError` for login, error, shell, or structure failures.
- `retrieve_tournament(url: str, requested_club: str, client: HttpClient) -> TournamentData` follows only links and request endpoints extracted from successfully parsed source pages; it uses the observed `/find/club/DoSearch` form only when exact affiliation matching is insufficient, and does not guess IDs or endpoint arithmetic.

- [ ] **Step 1: Write parser and retrieval tests against synthetic fixtures**

Fixtures use fictional players but the observed page shapes: event links such as `event.aspx?...&event=`, player links with source IDs, the empty player-list POST form, observed draw content form actions, `data-player-id`/`data-club-id`, `id="match_..."`, source round labels, pair entries, and published-empty match content. Tests assert registration/reserve/withdrawal status, mixed-club pairs, source links, match IDs, dates, empty schedule state, redirects, and distinction among login, 404, shell, and valid empty pages. The HTTP client tests assert bounded retry counts, no retries for permanent 4xx responses, per-run caching, and per-host pacing with an injected clock.

```python
def test_empty_schedule_is_not_a_parser_failure(empty_schedule_html):
    assert parse_match_list(empty_schedule_html, "https://example.test/matches") == ()
    assert classify_page(empty_schedule_html, ("matches",)) == PublicationState.PUBLISHED_EMPTY
```

Define `empty_schedule_html` in `tests/conftest.py` by reading the checked-in `tests/fixtures/empty-schedule.html` fixture.

- [ ] **Step 2: Run parser tests and confirm the missing interfaces fail**

Run: `python -m pytest -q tests/test_parsing.py tests/test_http_client.py`
Expected: collection fails because the client and parsers do not exist.

- [ ] **Step 3: Implement bounded HTTP retrieval**

Use one `requests.Session` with an identifying user agent, explicit connect/read timeouts, retries only for connection errors and transient 5xx/429 responses, one-second minimum spacing per host, standard safe redirect handling, and in-memory caching within the current run. Raise errors on non-success HTTP responses; do not retry permanent client errors or store any cache between runs.

- [ ] **Step 4: Implement page validation and parser functions**

Use BeautifulSoup with explicit expected markers. Extract event/draw/player IDs only from actual `href`, form actions, and data attributes. Submit the observed player-list form and issue observed draw-content requests. If the requested club does not exactly match affiliation labels, submit the requested string through the observed club-directory search form, use the directory source ID, and connect an affiliation label only when the token relationship is unique; preserve that resolution as a warning. Parse partner relationships from event entry rows and affiliations from the player-list response. Parse `GetDrawContent` by its actual `.bracket-round__item`, `.bracket-round__match-group-wrapper`, and `.match` markup. Build feeder edges only where the bracket's source layout establishes the relationship; if the mapping is not unambiguous, leave it unresolved. Parse source match IDs from the match element IDs in `GetMatchesContent`; preserve future nodes without unique source IDs using internal draw-position keys, never label those keys as source IDs. Treat an explicit empty schedule message as published-empty and “not planned” text as not published; fail if a required page is a login page, error page, shell, or unknown structure.

- [ ] **Step 5: Run retrieval and parsing tests**

Run: `python -m pytest -q tests/test_parsing.py tests/test_http_client.py`
Expected: fixtures prove the parser returns entries and pairs for known markup, returns an empty tuple only for an explicit source empty state, and raises typed errors for login, HTTP, and structural failures. A transient failure in one optional draw does not change it to unpublished; it adds a partial-extraction issue.

- [ ] **Step 6: Commit retrieval and parsing**

```bash
git add club_planner/http_client.py club_planner/parsing.py tests
git commit -m "feat: retrieve and parse tournament data"
```

## Task 3: Reachability, conditions, and additional-win depth

**Files:**
- Create: `club_planner/progression.py`
- Create: `tests/test_progression.py`

**Interfaces:**
- `compute_progression(matches: tuple[Match, ...], entries: tuple[Entry, ...], selected_player_ids: frozenset[str]) -> ProgressionResult`.
- A match's `feeder_ids` are references to source-backed predecessor match nodes; `Entrant.placeholder` stores a source-backed winner/group-place label when no player is confirmed.
- `Participation.additional_wins` counts only additional knockout wins required to enter the match; it is `None` when group qualification prevents an exact count.
- `Participation.conditions` preserves alternative path conditions as separate values; recorded results prune impossible branches without deleting historical matches.

- [ ] **Step 1: Write failing progression tests**

In `tests/test_progression.py`, define small frozen `Match` and `Entrant` fixtures directly (do not use network pages). Cover a knockout final, multiple alternatives converging on one deduplicated match, byes, recorded wins/losses, walkover/withdrawal/cancellation effects, a group stage with explicit group-winner/runner-up feeders, unresolved qualification, alternative opponents, mixed-club pairs, club-versus-club matches, eliminated-candidate pruning, exact additional-win counts, and distinct same-name player IDs.

```python
def test_bye_does_not_increase_additional_win_depth(knockout_matches):
    result = compute_progression(knockout_matches, (), frozenset({"p1"}))
    final = next(p for p in result.participations if p.player_id == "p1"
                 and p.match_id == "final")
    assert final.additional_wins == 2
```

Define `knockout_matches` in `tests/test_progression.py` as `qf1` (p1 versus p2), `qf2` (p3 versus p4), `semi` (winners of qf1/qf2), `semi_other` (a source-backed pair of unresolved quarterfinal winners), and `final` (winners of semi/semi_other). With qf1 unplayed, p1 needs one win to enter semi and two to enter final. Add a separate case where p1 is listed against a bye and enters the next round with zero additional wins.

- [ ] **Step 2: Run progression tests and confirm they fail**

Run: `python -m pytest -q tests/test_progression.py`
Expected: collection fails because `compute_progression` does not exist.

- [ ] **Step 3: Implement graph-based outcome and reachability logic**

Build adjacency only from `feeder_ids` parsed from source bracket groupings; never derive edges from match-number arithmetic or event chronology. Enumerate feasible alternatives recursively; require a published winner or feeder outcome to prune a branch. Do not emit a scheduled match row for a bye or count a bye as a win. Count only victories still needed after the current tournament state. For group qualifiers, preserve the condition and return `additional_wins=None`; use the separate knockout-after-qualification field only when that count is explicit. Keep completed matches as historical rows, and apply published walkover, withdrawal, and cancellation results according to their source outcomes.

- [ ] **Step 4: Run progression tests**

Run: `python -m pytest -q tests/test_progression.py`
Expected: test cases verify correct path conditions and win depths, updated results change reachability, eliminated players do not appear in future paths, shared matches are deduplicated, and unresolved group routes remain visible.

- [ ] **Step 5: Commit progression**

```bash
git add club_planner/progression.py tests/test_progression.py
git commit -m "feat: compute source-backed match progression"
```

## Task 4: Excel workbook generation

**Files:**
- Create: `club_planner/workbook.py`
- Create: `tests/test_workbook.py`

**Interfaces:**
- `write_workbook(data: TournamentData, progression: ProgressionResult, club: Club, output_path: Path) -> None` writes a temporary workbook in `output_path.parent`, validates it by reopening with openpyxl, then atomically replaces `output_path`.
- `safe_sheet_name(name: str, used_names: set[str]) -> str` removes Excel-invalid characters, truncates to 31 characters, and adds a deterministic suffix when needed.
- `progression_fill(additional_wins: int | None) -> PatternFill | None` returns no fill for current/unknown/group-qualified matches and a distinct fill for every numeric win depth.

- [ ] **Step 1: Write failing workbook tests**

Build synthetic domain records and assert sheets, English headings, one overview row per unique match, roster and entry coverage including withdrawn/reserve states, complete player/partner/opponent sides and clubs, conditions and possible-opponent alternatives, chronological date/time values, undated separation, source hyperlinks, retrieval metadata, partial-output warnings, literal `=`, `+`, `-`, and `@` values, unique long sheet names, frozen headings, filters, print settings, status text independent of fill, and distinct fills for depths 1, 2, and 3.

```python
def test_match_status_does_not_select_progression_fill(workbook_path):
    wb = load_workbook(workbook_path)
    ws = wb["Player"]
    assert ws["A2"].value == "Completed"
    assert ws["B2"].fill.fill_type is None
```

Create `workbook_path` in a `tmp_path` fixture by calling `write_workbook` with the synthetic tournament and progression records defined in `tests/test_workbook.py`.

- [ ] **Step 2: Run workbook tests and confirm they fail**

Run: `python -m pytest -q tests/test_workbook.py`
Expected: collection fails because workbook functions do not exist.

- [ ] **Step 3: Implement workbook sheets and safe cell writing**

Create `Club Overview`, unique player sheets, and `Legend & Info`. The overview includes date, local start time, event, draw/group, round, source match ID, complete sides, selected-club players, possible opponents and conditions, qualification conditions, per-player additional wins, venue, court, status, score, and source link. Player sheets include entries/partners plus the same relevant match details and progression conditions. Put undated or untimed rows in a clearly labeled section, sort dated values chronologically, and never synthesize Excel date/time values. Store user/source strings with openpyxl string cell types, set links only for validated HTTP(S) source URLs, add textual win-depth values, and style individual player participation cells rather than whole rows when depths differ. Keep status in a separate column. Show a prominent PARTIAL banner and each extraction issue whenever `TournamentData.partial` is true.

- [ ] **Step 4: Implement atomic save and workbook validation**

Save to a uniquely named temporary `.xlsx` beside the destination, reopen and inspect it with `load_workbook`, then use `os.replace`. On any exception, remove only that specifically created temporary file and leave an existing destination untouched.

- [ ] **Step 5: Run workbook tests**

Run: `python -m pytest -q tests/test_workbook.py`
Expected: loaded workbook has the required sheets, row values, hyperlinks, fill colors, literal content, and formatting; a simulated save failure leaves the prior destination bytes unchanged.

- [ ] **Step 6: Commit workbook generation**

```bash
git add club_planner/workbook.py tests/test_workbook.py
git commit -m "feat: generate club planning workbooks"
```

## Task 5: CLI, documentation, and live target workbook

**Files:**
- Create: `club_planner/cli.py`
- Create: `club_planner/__main__.py`
- Create: `tests/test_cli.py`
- Modify: `requirements.txt`
- Modify: `README.md`
- Generate: `planning.xlsx`

**Interfaces:**
- `build_parser() -> argparse.ArgumentParser` accepts required `--tournament-url`, `--club`, and `--output` values.
- `run(tournament_url: str, club_name: str, output: Path, client: HttpClient | None = None) -> TournamentData` retrieves, resolves, computes, and writes the workbook, raising actionable typed failures.
- `main(argv: list[str] | None = None, client: HttpClient | None = None) -> int` returns `0` for complete output, `2` after a valid but visibly partial workbook, and `1` when no trustworthy workbook was written; the optional client supports deterministic CLI tests.
- `python -m club_planner --tournament-url URL --club NAME --output FILE` starts a fresh retrieval and workbook generation.

- [ ] **Step 1: Write failing CLI orchestration tests**

Inject a fake client/source response to test required arguments, a successful entries-only run, a draw-without-times run, ambiguous club failure, a recoverable optional-draw failure that writes a marked partial workbook and returns `2`, login/parser failure with no workbook replacement, and that core failures leave an existing output file untouched.

```python
def test_cli_does_not_claim_success_for_login_page(tmp_path, fake_login_client):
    destination = tmp_path / "planning.xlsx"
    destination.write_bytes(b"existing")
    args = [
        "--tournament-url", "https://example.test/tournament/123",
        "--club", "Example Club",
        "--output", str(destination),
    ]
    assert main(args, client=fake_login_client) == 1
    assert destination.read_bytes() == b"existing"
```

Define `fake_login_client` in `tests/test_cli.py` as an `HttpClient` test double returning a 200 HTML response containing a login form and no tournament markers.

- [ ] **Step 2: Run CLI tests and confirm they fail**

Run: `python -m pytest -q tests/test_cli.py`
Expected: collection fails because the CLI entry points do not exist.

- [ ] **Step 3: Implement CLI orchestration and dependencies**

Implement argument parsing and orchestration with injectable retrieval for deterministic tests. Add requests, beautifulsoup4, and openpyxl to the existing pinned dependency file with pinned compatible versions. Keep each invocation fresh; do not introduce a persistent data cache or background process. For recoverable per-event/draw failures after core identity and roster retrieval, save an explicitly marked partial workbook and return `2`; for core failures return `1` without replacing the destination.

- [ ] **Step 4: Document installation, invocation, publication states, and limitations**

Update the README with dependency installation, the requested module invocation, workbook sheets, unique club-name resolution, request pacing, how to rerun after publication changes, and the fact that group progression is unresolved unless the source publishes the mapping.

- [ ] **Step 5: Run the complete automated suite**

Run: `python -m pytest -q`
Expected: all planner tests pass; existing scripts remain unchanged.

- [ ] **Step 6: Generate and inspect the target workbook**

Run:

```bash
python -m club_planner \
  --tournament-url "https://badvla.tournamentsoftware.com/tournament/046F75E1-3C36-4755-BD5E-C6488E44DE36" \
  --club "Pluimplukkers" \
  --output "planning.xlsx"
```

Open the generated workbook with openpyxl and verify the metadata and roster coverage, a selected-club knockout entry (Max Naessens), a mixed/doubles pairing, a source-backed later-round opponent/path, all player sheets, and warnings that schedule times are not published and the sampled group path is unresolved. Compare representative names, affiliations, pairings, bracket positions, and links against their live source pages. If the source structure has changed, stop with an explicit parser error rather than emitting a misleading workbook.

- [ ] **Step 7: Commit the CLI and documentation**

```bash
git add club_planner tests requirements.txt README.md
git commit -m "feat: add badminton club planner CLI"
```

## Plan Self-Review

- **Spec coverage:** Retrieval/parser distinction, club-directory alias IDs, pacing, retries, redirects, and partial-extraction behavior are covered by Tasks 1, 2, and 5; knockout, group, bye, result, deduplication, and unresolved logic by Task 3; workbook structure, roster coverage, safe names, literal text, colors, hyperlinks, and atomic writing by Task 4; CLI, dependencies, docs, and target workbook by Task 5.
- **Known target limitation:** The target has no published schedule times. Target group qualification to a playoff is not observed; only deterministic fixtures can verify that path.
- **Source ID limitation:** Future draw nodes may have source ID `0` or no unique published ID. The implementation uses draw structure for internal identity and never presents such an internal key as a source match identifier.
- **Subagent choice:** Execute inline in this session to keep live-source exploration, parser behavior, workbook output, and verification together.
