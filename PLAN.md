# Birthday Email Automation — Implementation Plan (Claude Planner)

This document is the authoritative implementation plan for the Codex Builder.
Follow it exactly; resolve any remaining ambiguity in favor of what is written
here. Do not re-litigate these decisions — implement them.

## 1. Architecture

A single-run Python 3.12+ CLI job (`run.py` → `app/main.py:main()`):

1. Load config from environment (`.env` via `python-dotenv` in local dev; real
   env vars in production).
2. Resolve "today" in `America/Chicago` (or `TEST_DATE` override).
3. Load spreadsheet rows via the configured `SpreadsheetProvider`
   (`google_sheet` or `xlsx_drive`).
4. Parse + validate each row into a `Client` model; bad rows are logged and
   skipped, never fatal.
5. Filter clients whose birthday month/day matches today (leap-day rule
   below).
6. For each match, atomically **claim** a send in SQLite, render the email,
   send via the `EmailProvider` (Gmail), and mark the claim `sent` or
   `failed` based on the provider's confirmed result.
7. Log a summary and exit 0. Never loops; never daemonizes.

No web server, no scheduler inside the process. Cron / Cloud Scheduler
triggers a fresh process each day.

## 2. Components

| Component | Responsibility |
|---|---|
| `app/config.py` | Parse & validate all env vars into a frozen `Config` dataclass. Fail fast with a clear error on invalid config. |
| `app/models.py` | `Client`, `BirthdayMatch`, `SendResult` dataclasses. |
| `app/birthday_service.py` | Orchestration: load rows → parse → match → claim → send → record. Pure-ish, takes injected collaborators (provider, state store, email provider, clock) for testability. |
| `app/spreadsheet/base.py` | `SpreadsheetProvider` ABC: `load_rows() -> list[dict[str, object]]` (see amendment in §7) plus header-resolution helper shared by both implementations. |
| `app/spreadsheet/google_sheets.py` | Reads a Google Sheet via Sheets API v4 (`spreadsheets.values.get`). |
| `app/spreadsheet/xlsx_drive.py` | Downloads an `.xlsx` from Drive (`files.get_media`/`export`) into memory, parses with `openpyxl`. |
| `app/state/sqlite.py` | Idempotency store: `claim(email, month, day, year) -> ClaimResult`, `mark_sent(claim_id)`, `mark_failed(claim_id)`. |
| `app/email/base.py` | `EmailProvider` ABC: `send(message: EmailMessage) -> None`, raises on failure. |
| `app/email/gmail.py` | Gmail API implementation (`users.messages.send`), builds MIME message (HTML + plain-text + optional inline image). |
| `app/templates/birthday_email.html` / `.txt` | Jinja2 templates, logic-free application code. |
| `app/retry.py` | Small `@retry_with_backoff` decorator for transient Google/Gmail API errors. |
| `app/birthday_rules.py` | Pure date-matching logic incl. Feb 29 rule; unit-tested in isolation. |
| `app/assets/birthday_banner.jpg` | Default placeholder birthday banner image. |
| `run.py` | Thin entrypoint calling `app.main.main()`. |

## 3. Dependencies (`pyproject.toml`)

Keep the dependency surface minimal and justified:

- `google-api-python-client`, `google-auth` — Sheets/Drive/Gmail API calls + service-account auth.
- `openpyxl` — `.xlsx` parsing (per spec, no alternative needed).
- `python-dotenv` — local `.env` loading only (never required in prod).
- `jinja2` — template rendering with conditional image blocks; avoids fragile manual string substitution.
- `tzdata` — guarantees IANA tz data on platforms without a system tzdb (safe to include; stdlib `zoneinfo` uses it if present).

Dev-only (`[dependency-groups].dev` or `[project.optional-dependencies]`):
`pytest`, `pytest-cov`, `ruff`, `mypy`.

No `pydantic`, no `tenacity`, no `freezegun` — implement config validation,
retry, and clock injection by hand; they're small and this keeps the
dependency count proportional to the task.

Set `requires-python = ">=3.12"` (the existing 3.14 venv still satisfies
this; do not narrow it to 3.14-only).

## 4. Folder Structure

Use the structure given in the spec verbatim:

```
app/{__init__.py,main.py,config.py,models.py,birthday_service.py,birthday_rules.py,retry.py}
app/spreadsheet/{__init__.py,base.py,google_sheets.py,xlsx_drive.py}
app/email/{__init__.py,base.py,gmail.py}
app/state/{__init__.py,sqlite.py}
app/templates/{birthday_email.html,birthday_email.txt}
app/assets/birthday_banner.jpg
tests/  (mirrors app/ layout: test_config.py, test_birthday_rules.py, test_birthday_service.py,
          test_spreadsheet_google_sheets.py, test_spreadsheet_xlsx_drive.py, test_state_sqlite.py,
          test_email_gmail.py, test_templates.py)
data/            # SQLite DB lives here at runtime; keep a .gitkeep, DB itself is gitignored
.env.example
.gitignore
pyproject.toml
README.md
Dockerfile
run.py
PLAN.md          # this file
```

Delete the placeholder `main.py` at repo root once `run.py` + `app/main.py`
exist (avoid two competing entrypoints).

## 5. Configuration (`app/config.py`)

Load via `os.environ` (with `python-dotenv` populating `os.environ` from
`.env` if present — never require `.env` in prod). Build a single frozen
`Config` dataclass. Validate eagerly; raise `ConfigError` with a specific,
non-secret-leaking message on any problem.

Full variable list (superset of the spec's `.env.example`):

```
APP_TIMEZONE=America/Chicago
DRY_RUN=true
TEST_DATE=

SPREADSHEET_MODE=google_sheet          # google_sheet | xlsx_drive

GOOGLE_SHEET_ID=
GOOGLE_SHEET_TAB=

GOOGLE_DRIVE_FILE_ID=

NAME_COLUMN=Name
EMAIL_COLUMN=Email
BIRTHDAY_COLUMN=Birthday
LAST_SENT_YEAR_COLUMN=Last Birthday Email Year

EMAIL_PROVIDER=gmail
EMAIL_FROM_NAME=
EMAIL_FROM_ADDRESS=
EMAIL_SUBJECT_TEMPLATE=Happy Birthday, {{name}}! 🎉

GOOGLE_CREDENTIALS_FILE=
GOOGLE_IMPERSONATE_SUBJECT=            # defaults to EMAIL_FROM_ADDRESS if blank

BIRTHDAY_IMAGE_MODE=local              # none | local | url — see note below
BIRTHDAY_IMAGE_PATH=app/assets/birthday_banner.jpg
BIRTHDAY_IMAGE_URL=
BIRTHDAY_IMAGE_ALT=Happy Birthday
BIRTHDAY_IMAGE_WIDTH=600

STATE_DB_PATH=data/birthday_state.db
STALE_CLAIM_TIMEOUT_MINUTES=30

RETRY_MAX_ATTEMPTS=3
RETRY_BASE_DELAY_SECONDS=1.0

LOG_LEVEL=INFO
```

Validation rules:
- `SPREADSHEET_MODE` must be one of the two literals.
- Google-sheet mode requires `GOOGLE_SHEET_ID`; xlsx-drive mode requires
  `GOOGLE_DRIVE_FILE_ID`.
- `EMAIL_FROM_ADDRESS` must look like an email address.
- `BIRTHDAY_IMAGE_MODE=local` requires `BIRTHDAY_IMAGE_PATH` to exist on
  disk at startup (fail fast, not mid-send). `=url` requires
  `BIRTHDAY_IMAGE_URL` to be `https://`. `=none` ignores both.
- `BIRTHDAY_IMAGE_WIDTH` must be a positive int.
- `TEST_DATE`, if set, must parse as `YYYY-MM-DD`; malformed → raise, never
  silently ignore (per spec).
- `DRY_RUN` parsed via a strict boolean parser (`true/false`, case-insensitive
  only — reject other values).
- `GOOGLE_CREDENTIALS_FILE` must exist on disk (not required only when both
  providers are fully mocked in tests — production always requires it).

**Amendment (post-Milestone-1 review):** the code-level and `.env.example`
default for `BIRTHDAY_IMAGE_MODE` was temporarily `none`, not `local`, for
Milestones 1-4. Milestone 5 lands the real committed asset at
`app/assets/birthday_banner.jpg` and flips the shipped default back to
`local`, restoring the intended out-of-the-box behavior without tripping
`load_config()`'s fail-fast local-image-path check.

## 6. Authentication Approach

Single Google **service account** JSON key (`GOOGLE_CREDENTIALS_FILE`),
loaded via `google.oauth2.service_account.Credentials`. This is the right
choice for an unattended daily batch job (Cloud Run Job / cron) — no
interactive OAuth consent, no refresh-token storage/rotation to manage.

- Scopes requested, minimal per use:
  - `https://www.googleapis.com/auth/spreadsheets.readonly` (google_sheet mode)
  - `https://www.googleapis.com/auth/drive.readonly` (xlsx_drive mode)
  - `https://www.googleapis.com/auth/gmail.send` (always, for sending)
- **Amendment (post-Milestone-6 review):** impersonation
  (`.with_subject(GOOGLE_IMPERSONATE_SUBJECT or EMAIL_FROM_ADDRESS)`) is
  used ONLY for the Gmail credential — Gmail send is a hard platform
  requirement (a bare service account cannot send mail as a real mailbox
  at all, delegated or not). Spreadsheet credentials (Sheets/Drive) are
  built WITHOUT `.with_subject()` — they always authenticate as the bare
  service account identity. This is simpler and more secure-by-default
  than the originally-planned "impersonate everywhere" design: it uses
  the minimum impersonation footprint needed (only where the platform
  requires it), and it makes the operator setup step identical
  regardless of whether domain-wide delegation is configured at all —
  the target Google Sheet or the `.xlsx` file in Drive is shared
  directly with the service account's own `client_email`, the same way,
  every time. Domain-wide delegation is still required (Workspace admin
  console) to authorize the `gmail.send` impersonation subject to send
  as that mailbox; it is not needed for, and has no effect on,
  spreadsheet access.
- Document in README: (1) share the Sheet/Drive file directly with the
  service account's `client_email` (Editor/Viewer as appropriate) — this
  is required in all cases; (2) configure Workspace domain-wide
  delegation for the service account so it may impersonate
  `GOOGLE_IMPERSONATE_SUBJECT`/`EMAIL_FROM_ADDRESS` specifically for the
  `gmail.send` scope.
- Never log credential contents or full tokens. `GOOGLE_CREDENTIALS_FILE`
  path may be logged; its contents never.

## 7. Spreadsheet Access Design

`app/spreadsheet/base.py` defines:

```python
class SpreadsheetProvider(ABC):
    def load_rows(self) -> list[dict[str, object]]: ...
```

Shared helper `resolve_headers(raw_header_row, required_logical_names, config)`:
normalizes header cells (`str.strip().casefold()`) and maps configured
logical names (`NAME_COLUMN` etc., also normalized) to actual column
indices. `LAST_SENT_YEAR_COLUMN` is optional (informational only — see §9,
it is not the idempotency source of truth); the other three are required or
`load_rows` raises `SpreadsheetError`.

**Amendment (post-Milestone-3 review):** row-building must preserve each
cell's native Python type (`str`, `date`, `datetime`, `int`, `float`) rather
than stringifying every value. §8's `parse_birthday` explicitly accepts
`date`/`datetime` passthrough and numeric Excel serials — stringifying a
birthday cell first (e.g. an Excel serial `36526` becoming the string
`"36526"`, or a native `datetime` becoming `"2000-01-01 00:00:00"`) breaks
that parser's contract and turns valid `.xlsx`/Sheets birthday values into
false "invalid row" skips. `build_row_dict`'s original signature
(`-> dict[str, str]`) was wrong for this reason; it is corrected to
`-> dict[str, object]`, only `.strip()`-ing values that are already `str`
and passing every other type through unchanged.

- `google_sheets.py`: build `googleapiclient.discovery.build("sheets","v4",...)`,
  call `spreadsheets().values().get(spreadsheetId=..., range=f"{tab}!A:Z")`
  (tab optional — default sheet if unset), first row = headers, remaining
  rows → list of dicts via `resolve_headers`. Wrap the API call in the
  retry decorator (transient 5xx/429 only).
- `xlsx_drive.py`: `drive_service.files().get_media(fileId=...)` streamed
  into an in-memory `io.BytesIO`, parsed with
  `openpyxl.load_workbook(buffer, data_only=True, read_only=True)`, first
  sheet unless a tab/sheet-name override is added later (not required by
  spec — first worksheet is fine). Same retry decorator around the
  download.
- Neither provider ever writes back to the spreadsheet — read-only by
  design (also why scopes are `.readonly`).

## 8. Birthday Parsing & Matching (`app/birthday_rules.py`)

`parse_birthday(raw: object) -> date | None` accepts, in order:
- `datetime.date` / `datetime.datetime` passed through directly (Sheets API
  returns numeric serials, not native dates — see below; `openpyxl` may
  hand back a real `datetime`/`date` for a numeric cell).
- Excel serial numbers (`int`/`float` — from `openpyxl` when a cell wasn't
  auto-converted, or from Sheets when `valueRenderOption` returns a
  serial): convert using the Excel epoch (`1899-12-30`).
- Strings, tried in order: `%m/%d/%Y`, `%-m/%-d/%Y` normalized via manual
  split (do not depend on platform-specific `%-m`), `%Y-%m-%d`,
  `%B %d, %Y` (e.g. "May 27, 2003").
- Returns `None` (never raises) on anything unparseable; caller logs the
  row index (not the raw client data) and skips it.

`is_birthday_today(birthday: date, today: date) -> bool`:
- Normal case: `birthday.month == today.month and birthday.day == today.day`.
- Feb 29 rule: if `birthday.month == 2 and birthday.day == 29`:
  - leap year today → match only on Feb 29.
  - non-leap year today → match on Feb 28 instead (so `is_birthday_today`
    returns `True` when `today == Feb 28` of a non-leap year for a Feb-29
    birthday). Implement by computing an "effective celebration date" for
    the given `today.year` and comparing.

## 9. Idempotency / Duplicate-Send Design (SQLite, `app/state/sqlite.py`)

**Critical component — implement exactly this state machine.**

Schema:

```sql
CREATE TABLE IF NOT EXISTS birthday_sends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_normalized TEXT NOT NULL,
    birthday_month INTEGER NOT NULL,
    birthday_day INTEGER NOT NULL,
    send_year INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','sent','failed')),
    claimed_at TEXT NOT NULL,
    sent_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (email_normalized, birthday_month, birthday_day, send_year)
);
```

`email_normalized` = `email.strip().lower()`. The SQLite DB is the sole
source of truth for "already sent this year" — the spreadsheet's
`Last Birthday Email Year` column, if present, is read and logged for
visibility only and is never written to and never used to gate sending.

Claim protocol (single method `claim(conn, email, month, day, year) ->
ClaimOutcome`, run inside `BEGIN IMMEDIATE`):

1. `INSERT INTO birthday_sends (..., status='pending', claimed_at=now, created_at=now)`.
   - Success (no constraint violation) → `ClaimOutcome.CLAIMED(row_id)`.
2. On `sqlite3.IntegrityError` (unique violation): `SELECT id, status,
   claimed_at FROM birthday_sends WHERE email_normalized=? AND
   birthday_month=? AND birthday_day=? AND send_year=?`.
   - `status == 'sent'` → `ClaimOutcome.ALREADY_SENT`.
   - `status == 'pending'` and `now - claimed_at < STALE_CLAIM_TIMEOUT_MINUTES`
     → `ClaimOutcome.IN_PROGRESS` (another worker/run owns it right now).
   - `status == 'failed'`, or `status == 'pending'` and stale →
     compare-and-swap: `UPDATE birthday_sends SET status='pending',
     claimed_at=now WHERE id=? AND status=<the status just read>`. If
     `cursor.rowcount == 1` → we won the reclaim →
     `ClaimOutcome.CLAIMED(row_id)`. Else another worker won the race →
     `ClaimOutcome.IN_PROGRESS`.
3. Commit the transaction that performed the winning INSERT/UPDATE before
   returning — the claim must be durable before any send attempt starts.

After attempting the send:
- Provider confirms success → `UPDATE ... SET status='sent', sent_at=now
  WHERE id=? AND status='pending'` (separate transaction). Only after this
  commits is the send considered final.
- Provider raises / returns failure → `UPDATE ... SET status='failed' WHERE
  id=? AND status='pending'`, and the client remains eligible for the next
  run (`ClaimOutcome.CLAIMED` again next time via the failed→pending CAS
  above).
- If the process crashes between claim and send, the row is left `pending`
  and gets reclaimed on the next run once `STALE_CLAIM_TIMEOUT_MINUTES`
  elapses — never send-then-never-record, and never stuck-forever.

Open the connection with `sqlite3.connect(path, timeout=30,
isolation_level=None)` and issue `BEGIN IMMEDIATE` explicitly for each
claim/update to serialize writers via SQLite's own file lock; retry once on
`sqlite3.OperationalError: database is locked` with a short sleep. Run
`PRAGMA journal_mode=WAL` at startup for better concurrent read/write
behavior.

`DRY_RUN=true` skips `claim()` and every state write entirely (per spec —
dry run must not write sent state).

## 10. Concurrency Protection

Production execution is a single sequential process (no threads/async
needed for throughput — birthday volume per day is small). "Concurrency
protection" means: **if the job is invoked twice around the same time**
(overlapping cron, manual + scheduled trigger, retpark after crash), two
independent processes hitting the same SQLite file must not both send to
the same client. This is guaranteed entirely by §9's claim protocol +
SQLite's file-level write serialization — no additional in-process locking
is needed. Add a dedicated test (`test_state_sqlite.py::test_concurrent_claim_is_exclusive`)
that opens two separate `sqlite3` connections to the same DB file and
issues concurrent claims for the identical key from two threads, then
asserts exactly one returns `CLAIMED` and the send-count of successful
claims is exactly one.

## 11. Email Architecture

`app/email/base.py`:

```python
@dataclass(frozen=True)
class EmailMessage:
    to_email: str
    to_name: str
    from_name: str
    from_address: str
    subject: str
    html_body: str
    text_body: str
    inline_image: InlineImage | None  # (content_id, bytes, mime_type) — local mode only


class EmailProvider(ABC):
    def send(
        self, message: EmailMessage
    ) -> None: ...  # raise EmailSendError on failure
```

`app/email/gmail.py`: builds a `MIMEMultipart("related")` containing a
`MIMEMultipart("alternative")` (text/plain + text/html parts) and, when
`inline_image` is set, a `MIMEImage` with `Content-ID: <birthday_banner>`
and `Content-Disposition: inline`. Base64/urlsafe-encode the raw RFC 2822
message and call `users().messages().send(userId="me",
body={"raw": ...})`. On any failure raise `EmailSendError` (never let a
raw googleapiclient exception escape past this module).

**Amendment (post-Milestone-5 review):** do NOT wrap the `messages.send`
call itself in the transient-retry decorator, unlike the read-only Sheets
and Drive calls. `send` is a non-idempotent write with no
Gmail-API-provided idempotency key — if the request reaches Gmail and
succeeds but the response is lost to a transport error, an automatic
in-process retry would send a second, real duplicate email. Removing
in-process retry closes that specific window, but does NOT by itself make
cross-run reclaim (§9) safe for this same failure mode: a `failed` row is
eligible for reclaim on a later run, and if the original failure was
"ambiguous" (the request may have actually reached Gmail and succeeded
before the response was lost), that later reclaim can still send a real
duplicate — just spread across runs instead of within one process.

A full fix (checking Gmail's Sent mail for a deterministic Message-ID
before reclaiming) would require a broader OAuth scope than `gmail.send`
and meaningful new reconciliation logic — disproportionate engineering
for this project. The proportionate mitigation instead: `GmailProvider`
distinguishes *pre-dispatch* failures (message construction, anything
before `.execute()` is called — definitely not sent, always safe to
retry) from *post-dispatch* failures (the `.execute()` call itself
raised — outcome unknown, Gmail may have already accepted it) by raising
a dedicated `AmbiguousSendError(EmailSendError)` for the latter case.
**Milestone 6 requirement (refined post-Milestone-6 review):**
when `birthday_service` catches `AmbiguousSendError`, it must NOT call
`mark_failed()` — a `failed` row has no staleness gate and becomes
immediately reclaimable on literally the very next `claim()` attempt
(including an operator-triggered manual rerun moments later), which
defeats the purpose of surfacing this case distinctly at all. Instead,
leave the row exactly as `claim()` left it (`pending`) — untouched — so
it only becomes reclaimable after `STALE_CLAIM_TIMEOUT_MINUTES` elapses,
the same as any other unresolved claim. That reuses the existing
staleness mechanism (no new terminal status, no schema change, no
reconciliation workflow — a full quarantine state was already rejected
above as disproportionate engineering) to buy a real grace window
(default 30 minutes) between the prominent `CRITICAL` log and the
earliest possible reclaim, giving an operator a genuine chance to check
the mailbox first. It must still log a distinct, prominent warning
(`CRITICAL`, not the routine failure log level) naming the client and
stating the send outcome is unknown and a future reclaim could
double-send. This does not eliminate the residual risk, but makes it
visible and rare
(it requires a successful request whose specific response is then lost)
rather than silent.

**Known limitation (accepted):** `main()` exits non-zero on the run that
*detects* an ambiguous send (`summary.ambiguous > 0`), which is when the
CRITICAL log is emitted. If an operator or scheduler reruns the job
before `STALE_CLAIM_TIMEOUT_MINUTES` elapses, that rerun sees the row as
`IN_PROGRESS` (not `ambiguous`) and can exit 0, even though the original
issue is still unresolved underneath. Closing this gap properly would
require persisting additional state to distinguish "routine concurrent
`IN_PROGRESS`" from "unresolved ambiguous send awaiting verification" —
i.e. the same quarantine/reconciliation machinery already rejected above
as disproportionate for this project. The operator has already seen the
CRITICAL log naming the exact risk at detection time; this is accepted
as a narrow, documented residual limitation rather than a bug to
engineer around.

**Known limitation (accepted):** Milestone 6's lazy construction of
`StateStore`, the `EmailProvider`, and the local inline-image bytes
(sections above) means a dry-run or a genuine zero-birthday-today
production run never touches Gmail auth, the SQLite state file, or the
local image path at all. This is an intentional trade-off, not an
oversight: it's the direct fix for the earlier, symmetric problem where
those same no-op runs were failing hard on unrelated credential/DB/image
issues (see the lazy-construction fixes above). The flip side is real —
a broken Gmail delegation, an unwritable `STATE_DB_PATH`, or a corrupted
local image can go undetected through any number of clean-looking
zero-match days, surfacing only on the first day a birthday actually
needs to be sent. A proper fix (an explicit strict-validation/healthcheck
mode that eagerly exercises the full send path regardless of whether
anything will be sent today) is genuinely new scope beyond this
project's original spec — it is not implemented here. Operators who want
continuous readiness signal should periodically exercise the real send
path deliberately (for example a scheduled `DRY_RUN=false` run against a
synthetic test recipient/date via `TEST_DATE`, run outside the normal
daily schedule) rather than relying on an ordinary day's clean exit code
as proof the send path works.

Subject default: `Happy Birthday, {{name}}! 🎉` rendered via
`EMAIL_SUBJECT_TEMPLATE` (Jinja2), same templating engine as the body so
there's one substitution mechanism.

## 12. Birthday Email Design / Templates

`app/templates/birthday_email.html` structure (Jinja2, rendered by
`birthday_service`):

1. Headline: `Happy Birthday, {{ name }}! 🎉`
2. Personalized greeting line.
3. Image block, conditional:
   - `image_mode == "local"` → `<img src="cid:birthday_banner" alt="{{ image_alt }}" width="{{ image_width }}">`
   - `image_mode == "url"` → `<img src="{{ image_url }}" alt="{{ image_alt }}" width="{{ image_width }}">`
   - `image_mode == "none"` → block omitted entirely.
4. Warm birthday message paragraph.
5. Signature block using `EMAIL_FROM_NAME` / company name.

`birthday_email.txt` mirrors the same content with no markup (image mode
becomes, at most, a plain URL line for `url` mode; nothing for
`local`/`none`, since inline attachments have no meaningful plain-text
form).

Templates contain **no application logic** — only variables the service
passes in: `name`, `image_mode`, `image_alt`, `image_width`, `image_url`.

## 13. Birthday Image Implementation

- `none`: `image_mode="none"` passed to template, no attachment built.
- `local`: `birthday_service` reads `BIRTHDAY_IMAGE_PATH` bytes at startup
  (already validated to exist by `config.py`), builds `InlineImage(content_id="birthday_banner",
  data=..., mime_type=<sniffed from extension>)`, passed to
  `EmailMessage.inline_image`. Gmail provider attaches it as
  `Content-ID: <birthday_banner>`; template references `cid:birthday_banner`.
  No `file://` URL ever touches the HTML.
- `url`: no attachment; template embeds `BIRTHDAY_IMAGE_URL` directly, must
  be validated `https://` at config time.
- Include a real placeholder `app/assets/birthday_banner.jpg` so `local`
  mode works out of the box.

## 14. Retry Behavior (`app/retry.py`)

A small decorator: `retry_with_backoff(max_attempts, base_delay_seconds,
retryable_exceptions)`. Retries only on the transient exception types
passed in (e.g., `googleapiclient.errors.HttpError` with status in
`{429,500,502,503,504}`, `TimeoutError`, `ConnectionError`) with
`base_delay * 2**attempt` sleep. Never retries validation errors
(`ConfigError`, `SpreadsheetError` for malformed data, `ClaimOutcome`
logic) — those are permanent by construction and simply propagate/are
logged and skipped.

## 15. Dry Run & Test Date

- `TEST_DATE` parsed in `config.py`; `birthday_service` asks a small
  `Clock` abstraction (`today() -> date`) for "today" — production clock
  uses `datetime.now(ZoneInfo(APP_TIMEZONE)).date()`; when `TEST_DATE` is
  set, the clock returns that fixed date instead. This is the single
  seam tests use instead of a mocking library.
- `DRY_RUN=true`: run the full pipeline (load, parse, match, render,
  validate) but skip both `EmailProvider.send()` and any SQLite write —
  log `"[DRY RUN] would send to <normalized-email-domain-redacted-or-not>..."`
  at INFO with enough detail to be useful without dumping full client PII
  (name/email may be logged in dry-run explicitly since spec says "log
  what would happen" and dry-run is an operator-facing debug mode — full
  address is fine here, just don't dump irrelevant columns).

## 16. Logging

Standard `logging`, configured once in `app/main.py` from `LOG_LEVEL`.
One logger per module (`logging.getLogger(__name__)`). Log at minimum, at
INFO unless noted: start (with effective date + spreadsheet source +
dry-run flag), spreadsheet load success + row count, birthdays detected
count, per-send outcome (sent/duplicate-skipped/failed) by normalized
email only (not full record), invalid-row count (WARNING, with row index),
fatal errors (ERROR/CRITICAL with exception info), and a final one-line
summary (`inspected=N matched=N sent=N duplicates=N invalid=N failed=N`).
Never log credential file contents, raw API tokens, or the full spreadsheet
row.

## 17. Testing Strategy

`pytest`, all 20 spec-listed cases mapped to concrete tests:

| # | Case | Test location |
|---|---|---|
|1,2,3| birthday today / none / multiple | `test_birthday_service.py` |
|4,5,6,7| invalid/missing birthday, missing/invalid email | `test_birthday_rules.py`, `test_birthday_service.py` |
|8,9| Feb 29 leap / non-leap | `test_birthday_rules.py` |
|10,11| duplicate same year / retry after failure | `test_state_sqlite.py` |
|12| dry run | `test_birthday_service.py` |
|13| TEST_DATE | `test_config.py`, `test_birthday_service.py` |
|14| bad rows don't interrupt good ones | `test_birthday_service.py` |
|15,16,17| local/url/none image | `test_email_gmail.py`, `test_templates.py` |
|18| spreadsheet mode selection | `test_config.py` / `test_birthday_service.py` (factory test) |
|19| concurrent duplicate protection | `test_state_sqlite.py` (see §10) |
|20| provider failure handling | `test_birthday_service.py` (fake provider raises → state stays `failed`, no crash) |

All Google API calls mocked (fake `SpreadsheetProvider`/`EmailProvider`
implementations or `unittest.mock.patch` on the `googleapiclient` build
call) — **tests must never perform real network I/O or send real email.**
Use `tmp_path` for SQLite DB files in tests. Target: all new modules
covered; no arbitrary coverage percentage gate.

## 18. Quality Checks

- `pytest -q` must pass.
- `ruff check .` must pass (configure in `pyproject.toml`, reasonably
  standard ruleset, no project-specific exotic config).
- `ruff format --check .` for formatting.
- `mypy app` — keep practical; it's fine to add narrow `# type: ignore`
  for the Google API client's dynamically-typed `build()` return if typing
  it fully isn't worthwhile.

## 19. Deployment Strategy

- **Local**: `uv run run.py` (or `python run.py` inside the venv) after
  populating `.env` from `.env.example`.
- **cron**: example line running daily at 08:00 America/Chicago,
  `cd /opt/birthday-automation && /usr/bin/env -S uv run run.py >>
  /var/log/birthday-automation.log 2>&1`.
- **Docker**: slim `python:3.12-slim` base, install deps, `COPY` app,
  `ENTRYPOINT ["python","run.py"]`, no `CMD` loop — one run per container
  invocation, `.env`/secrets mounted or passed via `--env-file`/orchestrator
  secret injection, never baked into the image.
- **Cloud**: document Google Cloud Run Jobs (not Cloud Run Service — this
  is a batch job, not a server) + Cloud Scheduler triggering the Job
  execution daily via the Cloud Run Jobs API/`gcloud run jobs execute`.
  Credentials via Secret Manager mounted as a file or the service account
  attached directly to the Job (preferred — no key file needed at all when
  running on GCP: the Cloud Run Job's attached service account can be used
  directly by `google.auth.default()` as a fallback when
  `GOOGLE_CREDENTIALS_FILE` is unset). Note this as an optional enhancement
  in README, not required for milestone completion.

## 20. Git Workflow Considerations

- Repo already has `origin` → `https://github.com/E-techgod/bday-automatization.git`,
  branch `main`, gh CLI authenticated. Work directly on `main` with small,
  reviewed commits per milestone (no established branching strategy exists
  yet, so introducing one is unnecessary ceremony for a solo-operated repo).
- `.gitignore` must cover: `.env`, `*.env` (but not `.env.example`),
  `GOOGLE_CREDENTIALS_FILE` target patterns (`*credentials*.json`,
  `*service-account*.json`), `data/*.db`, `data/*.db-journal`,
  `data/*.db-wal`, `data/*.db-shm`, `__pycache__/`, `.pytest_cache/`,
  `.ruff_cache/`, `.mypy_cache/`, `*.egg-info/`, `.venv/` (already present),
  `.coverage`.
- Never commit `.venv/` contents, any real credentials, or a populated
  `.env`.

## 21. Implementation Order (Milestones)

Each milestone is one Builder→Reviewer round-trip; commit + push only after
PASS.

1. **Scaffold & config** — folder structure, `pyproject.toml` deps,
   `.gitignore` hardening, `app/config.py` + `ConfigError`, `.env.example`,
   remove root `main.py`, add `run.py` stub. Tests: `test_config.py`.
2. **Domain models & birthday rules** — `app/models.py`,
   `app/birthday_rules.py` (parsing + Feb 29 matching + Clock). Tests:
   `test_birthday_rules.py` (cases 4,5,6,7,8,9,13).
3. **Spreadsheet layer** — `base.py` + `google_sheets.py` + `xlsx_drive.py`,
   both mocked in tests (case 18). No live network.
4. **SQLite idempotency state** — `app/state/sqlite.py` full claim
   protocol from §9. Tests: `test_state_sqlite.py` (cases 10, 11, 19).
5. **Email layer** — `app/email/base.py` + `gmail.py`, templates,
   image modes (§12–13), placeholder `birthday_banner.jpg`. Tests:
   `test_email_gmail.py`, `test_templates.py` (cases 15,16,17).
6. **Orchestration** — `app/birthday_service.py` wiring everything +
   `app/retry.py` + `app/main.py` + logging (§16) + dry-run (§15). Tests:
   `test_birthday_service.py` (cases 1,2,3,12,14,20 + integration of the
   rest).
7. **Quality pass** — ruff/mypy config finalized, full suite green,
   `pyproject.toml` finalized.
8. **Docker + deployment docs** — `Dockerfile`, deployment section of
   README (§19).
9. **README + final production review** — full README per spec's
   required sections, final Reviewer pass against the complete
   Completion Conditions checklist.

Builder may combine trivially small steps but must not skip the
Reviewer gate between milestones 4, 5, 6 (idempotency, email/image, and
orchestration are the highest-risk, most-scrutinized areas per the
Reviewer checklist) and must not batch multiple milestones into a single
uncontrolled commit.
