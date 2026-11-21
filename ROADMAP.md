# Roadmap

Things I might add to survey-builder. The 1.0.0 release covers the whole loop
(build, publish, collect, read the results, export), so nothing here is
promised or scheduled. These are ideas, written down with enough detail that I
(or anyone else) can pick one up later without starting from zero. Items may
change, move between groups or be dropped.

What the app does today is in the [README](README.md) and the notes under
[docs/](docs/).

- **Next**: small or well understood. I would start with these.
- **Later**: worth doing, but bigger or waiting on a decision.
- **Maybe**: not sure yet that they are worth the extra complexity.

Sizes are rough: **S** is an evening or two, **M** a few evenings up to a
couple of weekends, **L** several weeks of spare time.

Each item is meant to fit in one pull request and to be covered by the test
suite. There are no browser tests: everything under `tests/` is pytest, either
calling the modules in `survey_builder/domain/` directly or driving the Flask
test client (with `tests/factories.py` for data). The suite runs on in-memory
SQLite and, in CI, a second time on PostgreSQL, so queries must work on both.
Logic worth testing (validation, branching, aggregation, export) belongs in
`domain/`, not in a view or a template, as `CONTRIBUTING.md` already asks.
Schema changes come with an Alembic migration under `migrations/versions` and,
per the upgrade promise in `docs/deployment.md`, only add tables, columns and
indexes. File names below are relative to `survey_builder/` unless they start
with `tests/`, `docs/`, `migrations/` or are a root file.

"Depends on" lists real prerequisites only. Items that merely touch the same
file are not listed there; the bigger overlaps are mentioned in the items.

When an item ships, its row in the Overview says `Shipped` in the Group column
and its section moves under a `## Shipped` heading at the end, shortened to one
paragraph on what was built and where it differs from the text here. The same
pull request updates the README, the matching page under `docs/` and adds an
entry under `## [Unreleased]` in the CHANGELOG.

## Overview

| #   | Item                                          | Group | Area      | Size | Depends on |
| --- | --------------------------------------------- | ----- | --------- | ---- | ---------- |
| 1   | Warn before edits that change collected data  | Next  | editor    | M    | -          |
| 2   | Progress that does not outgrow the cookie     | Next  | public    | M    | -          |
| 3   | Close sign-up                                 | Next  | accounts  | S    | -          |
| 4   | Spam protection on public links               | Next  | public    | S    | -          |
| 5   | Hidden fields from the link                   | Next  | public    | M    | -          |
| 6   | Outgoing email and password reset             | Later | accounts  | M    | -          |
| 7   | Tell the owner about new responses            | Later | results   | S    | 6          |
| 8   | Webhooks for completed responses              | Later | api       | M    | -          |
| 9   | API tokens                                    | Later | api       | M    | -          |
| 10  | Skip rules on ratings, NPS and numbers        | Later | logic     | M    | -          |
| 11  | Show a question only if                       | Later | logic     | M    | -          |
| 12  | Earlier answers inside later questions        | Later | logic     | S    | -          |
| 13  | Dropdown and yes/no questions                 | Later | questions | S    | -          |
| 14  | "Other, please specify"                       | Later | questions | M    | -          |
| 15  | Ranking questions                             | Later | questions | M    | -          |
| 16  | Matrix questions                              | Later | questions | L    | -          |
| 17  | Opening date and scheduled closing time       | Later | sharing   | S    | -          |
| 18  | Response limit that holds under load          | Later | sharing   | S    | -          |
| 19  | Redirect after the last page                  | Later | sharing   | S    | 5          |
| 20  | QR code for the share link                    | Later | sharing   | S    | -          |
| 21  | Excel export                                  | Later | results   | S    | -          |
| 22  | Cross tabulation                              | Later | results   | M    | -          |
| 23  | Shareable results page                        | Later | results   | M    | -          |
| 24  | Print-friendly results                        | Later | results   | S    | -          |
| 25  | Results computed in the database              | Later | results   | L    | -          |
| 26  | Automatic cleanup and response retention      | Later | ops       | S    | -          |
| 27  | Sign-in throttling shared by every worker     | Later | accounts  | S    | -          |
| 28  | Collaborators on a survey                     | Later | accounts  | L    | -          |
| 29  | Respondent pages in other languages           | Later | public    | M    | -          |
| 30  | Accessibility pass on the respondent pages    | Later | public    | M    | -          |
| 31  | Dark mode                                     | Later | ui        | S    | -          |
| 32  | Browser tests for the editor                  | Later | tests     | M    | -          |
| 33  | Invitation lists with one-time links          | Maybe | sharing   | L    | 6          |
| 34  | File upload questions                         | Maybe | questions | L    | -          |
| 35  | Quotas                                        | Maybe | sharing   | M    | 18         |
| 36  | Multilingual surveys                          | Maybe | public    | L    | 29         |
| 37  | Survey versions                               | Maybe | editor    | L    | 1          |
| 38  | Two-factor sign-in                            | Maybe | accounts  | M    | -          |

## Next

### 1. Warn before edits that change collected data

The editor treats a survey with 140 responses like a fresh draft. Every
change is saved at once, and several of them quietly rewrite or remove
results:

- Deleting a choice (`delete_choice` in `editor.py`) deletes every answer
  that picked it, through `ondelete="CASCADE"` on `Answer.choice_id`. The
  charts change and the CSV loses the values, with no warning.
- Deleting a question or a page does the same for all its answers.
- Changing settings through `update_question` keeps old answers that no
  longer fit: a rating scale cut from 10 to 5 leaves answers of 8 that
  `_summarize_scale` in `domain/results.py` does not place on the chart,
  and a choice relabelled from "Yes" to "No" changes the meaning of every
  stored answer.

Plan:

- A pure `edit_impact(survey, change)` in a new `domain/edit_impact.py`
  that says how many completed responses a change touches and whether it
  deletes or reinterprets data. The views ask it before saving.
- Deleting a choice, question or page with answers needs a confirmation
  that names the number ("37 responses answered this question. Their
  answers will be deleted."). With htmx that is a small confirm fragment
  in place of the button; without JavaScript, a confirm page.
- Settings that make old answers invalid (a smaller scale, a tighter
  number range) are refused once there are answers, with a hint to
  duplicate the question instead. Relabelling is allowed but warns.
- Adding things (questions, choices, pages) stays free.
- Tricky: incomplete responses. They do not show in results but are kept
  for the completion rate. Count only completed ones in the message; the
  incomplete ones lose answers too, which is fine.
- Undecided: an "archive choice" that hides it from new respondents but
  keeps old answers. Useful, and it needs a column on `Choice`; I lean
  towards doing it in this item, since it is the honest answer to "I want
  to remove this option".
- Tests: unit tests for `edit_impact`; client tests for the confirm flow
  in `tests/test_editor_choices.py` and `tests/test_editor_questions.py`.

### 2. Progress that does not outgrow the cookie

The respondent's progress lives in the signed session cookie under
`survey:<token>` (`load_state` and `save_state` in `public.py`): the
response key, the page, the history and, after Back, a draft of every field
on the page. A long text question allows up to 5,000 characters
(`question_types.py`), and browsers drop cookies over about 4 KB. Someone
who writes a long answer and presses Back gets a cookie the browser throws
away, and with it the whole session: they land on page one with a new
response key. Several surveys open in the same browser share the same
cookie too.

- Keep only the response key and a few ids in the cookie. Drafts go to the
  database: a `draft` JSON column on `Response`, or a small `ResponseDraft`
  table keyed by response and page.
- That needs a `Response` row before the first valid submit, which the
  current design avoids on purpose so that people who only open the link
  are not counted. Create the row on the first Back or the first submit,
  whichever comes first, and keep counting "started" from the first
  submit with a separate `first_submitted_at` so the completion rate does
  not change meaning.
- Werkzeug logs a warning when a cookie is too large; add a check in the
  test client so a regression fails a test instead.
- Tests: `tests/test_public_submit.py` with a 5,000 character draft,
  Back, then forward again; a test that only opening the link still
  creates nothing.

### 3. Close sign-up

`/register` in `auth.py` is open to anyone who can reach the site. For a
team running its own copy that means strangers can create accounts and
publish surveys from the company's domain. There is no switch.

- `REGISTRATION=open|closed` (default `open`, to keep today's behaviour).
  Closed hides the link, answers 404 on `/register` and leaves
  `flask create-user` as the way to add people.
- Optionally an allow list of email domains (`REGISTRATION_DOMAINS`), so a
  company can keep sign-up open to its own addresses.
- Document it in `docs/deployment.md` next to the first-account step.
- Tests: `tests/test_auth.py` and `tests/test_config.py`.

### 4. Spam protection on public links

A public link accepts any number of submissions. Kiosk mode aside, the only
guard against repeats is the session cookie, which a script simply does not
send back. Bots that find a form fill every field, and one person can skew
an NPS by clearing cookies.

- A honeypot field in `public/page.html`, hidden from people and screen
  readers, that real browsers leave empty.
- A minimum time between rendering the first page and the first submit
  (two seconds), checked from a timestamp in the state.
- A per address limit on new responses per survey per hour, counted in the
  database (`Response` gets a hashed client address column, hashed with
  the secret key and the survey id so it cannot be joined across surveys).
  The trusted proxy setting already gives the real address.
- Rejected submissions look like success to the client, so bots learn
  nothing, and are not stored.
- Tricky: kiosk mode, where one device submits many responses on purpose.
  The address limit has to be off or much higher there.
- Tricky: respondents behind one company NAT. Make the limit a survey
  setting with a generous default (say 50 an hour) rather than a constant.
- Undecided: a self-hosted captcha. Not in this item; the three checks
  above stop the cheap bots.
- Tests: client tests for each check, including kiosk mode.

### 5. Hidden fields from the link

Owners often know who they are sending a survey to: a customer id from the
CRM, the channel (`?src=newsletter`), a store number. Today the only way to
get that into the results is to ask the respondent.

- A list of hidden field names per survey, set on the settings page.
  Values come from the query string of the share link
  (`/s/TOKEN?customer=123`), are captured on the first page view, stored in
  the state and written to the response on the first submit.
- Storage: a `hidden` JSON column on `Response`. Shown on the individual
  response page, as extra columns in the CSV (`domain/export.py`) and in
  the API.
- A filter by hidden value in `ResponseFilter`, next to the date and choice
  filters.
- Tricky: anonymity. The README promises anonymous respondents; a customer
  id ends that. The settings page should say so, and the public page could
  say "This survey records where you came from" when hidden fields are on.
- Tricky: only declared names are stored, with a length limit, so a link
  cannot be used to write arbitrary data.
- Tests: client tests in `tests/test_public_submit.py`; export tests for
  the extra columns.

## Later

### 6. Outgoing email and password reset

The app sends no email at all. Someone who forgets the password has no way
back except an operator running `flask create-user` again under another
address. Items 7 and 33 need email too.

- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`,
  `MAIL_FROM` and `MAIL_TLS` in `config.py`. Without `MAIL_SERVER` email is
  off and the reset link is not shown. Sending through the standard library
  `smtplib`; no new dependency is needed.
- A mailpit service in `docker-compose.yml` for the demo.
- Password reset: a signed, time-limited token (itsdangerous, already a
  Flask dependency) that includes the user's `session_version`, so it stops
  working once the password changed or the user signed out everywhere.
- The reset page answers the same whether the address exists or not.
- Tests: a fake mail backend collecting messages; reset flow tests in
  `tests/test_auth.py`, including an expired and a reused token.

### 7. Tell the owner about new responses

Owners have to open the dashboard to see whether anyone answered.

- A per survey setting: email me on every response, once a day, or never.
- The daily digest needs a scheduler. The app has none; a `flask
  send-digests` command run from cron, like `prune-incomplete`, keeps it
  that way.
- Tests: digest content as a unit test; the command in `tests/test_cli.py`.

### 8. Webhooks for completed responses

People want responses in their own tools (a sheet, a CRM, a chat channel)
without polling the API.

- A webhook URL and secret per survey. On completion the app posts the
  response as JSON (the same shape as the API), signed with HMAC-SHA256.
- Delivery must not slow down the respondent's last submit. Without a task
  queue in the stack, write a row to a `webhook_deliveries` table in the
  submit transaction and send from a `flask deliver-webhooks` loop that
  runs as a second process in compose.
- Retries with backoff, a delivery log on the settings page, a test
  button.
- Tests: signature unit tests; delivery loop tests with a fake HTTP
  client.

### 9. API tokens

The JSON API (`api.py`) uses the session cookie. A script or a dashboard
cannot use it without copying a browser cookie, which expires and carries
full account rights.

- Personal tokens on the account page: a name, read-only scope (the API
  has nothing else yet), created and last used dates. Only a hash is
  stored; the token is shown once.
- `Authorization: Bearer` accepted by the API blueprint next to the
  session; other blueprints ignore it.
- `docs/api.md` gets curl examples.
- Tests: `tests/test_api.py` with a token, a revoked token and a token of
  another user.

### 10. Skip rules on ratings, NPS and numbers

Skip rules (`BranchRule`, `domain/branching.py`) work on choices only: "if
this choice was picked, go to that page". The most common rule in feedback
surveys, "if the NPS is 6 or lower, ask why", cannot be written.

- A rule gets an operator and a value as an alternative to `choice_id`:
  `<=`, `>=`, `=` on rating, NPS and number answers.
- `next_page` checks them in the same order as today: question by question,
  first match wins.
- The editor's rule form shows the fitting inputs per question type.
- Tricky: `prune_invalid_rules` and the "pages nobody can reach" warning
  must understand the new rules.
- Tests: `tests/test_branching.py` for each operator; an editor test.

### 11. Show a question only if

Skip rules move between pages. Hiding one follow-up question on the same
page ("Which one?" only when "Other tools" was ticked on the previous page)
needs a page of its own today.

- A display condition on `Question`: show it only when an earlier question
  (on an earlier page) has a given answer. Stored in `settings` or a small
  table; the same operators as item 10.
- `parse_page` in `domain/answers.py` skips hidden questions, so a required
  hidden question does not block the page.
- Results say how many respondents saw the question, not only how many
  answered.
- Tricky: conditions on the same page need JavaScript to show and hide
  live. Limiting conditions to earlier pages keeps the app working without
  JavaScript, which `docs/architecture.md` promises.
- Tests: unit tests for the visibility function; client tests.

### 12. Earlier answers inside later questions

"What could we do better at {{q3}}?" with the store picked earlier is a
common request and cheap once answers are at hand.

- A placeholder syntax in prompts and help text that names an earlier
  question, filled from the stored answers when the page renders.
- The editor offers the placeholder from a menu, so nobody types ids.
- Tricky: the answer is respondent text inside the prompt. It goes through
  Jinja's escaping like everything else, never `|safe`.
- Tests: unit tests for the substitution; a public page test.

### 13. Dropdown and yes/no questions

Single choice with forty options (countries, departments) is a wall of
radio buttons; yes/no is a single choice with two options that every owner
builds by hand.

- `dropdown`: a single choice question rendered as `<select>`, same storage
  and results as single choice.
- `yes_no`: a single choice with two fixed choices created with the
  question, labels editable.
- Both in `question_types.py`, the editor, the templates
  (`templates/editor/`), results and export.
- Tests: the existing per type tests extended.

### 14. "Other, please specify"

A choice question cannot have a free text "Other" option, so owners add a
separate short text question after it.

- A per choice flag `allows_text`. When that choice is picked, a text input
  next to it is required.
- Stored as the choice answer plus `text_value` on the same `Answer` row,
  which the model already allows.
- Results show the "Other" texts like a short text question; the CSV gets
  a column for them.
- Tests: `tests/test_answers.py` for validation; export tests.

### 15. Ranking questions

"Put these in order of importance" has no good substitute.

- A `ranking` type with choices; the respondent orders them.
- Without JavaScript: a number select next to each option, validated as a
  permutation. With JavaScript, drag and drop or up and down buttons on
  top of the same fields.
- Stored as one `Answer` per choice with its rank in `number_value`.
- Results: average rank and how often each option came first.
- Tests: validation and aggregation units; a client test.

### 16. Matrix questions

A block of statements rated on the same scale ("Rate each: price, quality,
support") is the most requested question type in survey tools and the
biggest change on this list, because it has rows and columns.

- A `matrix` type with rows (statements) and columns (scale labels). Rows
  reuse `Choice`; columns live in `settings`.
- Stored as one `Answer` per row with the column index in `number_value`.
- Results: one stacked bar per row; the CSV gets one column per row.
- Tricky: small screens. A table of radio buttons does not fit a phone;
  render each row as its own group below a breakpoint.
- Tricky: skip rules and conditions on a matrix row. Leave them out.
- Tests: validation, results and export units; a client test.

### 17. Opening date and scheduled closing time

`closes_on` is a date and closes at the end of that day in UTC
(`closed_reason` in `domain/sharing.py`). There is no opening date, and
"closes at 17:00 local time" cannot be set.

- `opens_at` and `closes_at` as timestamps with a time zone chosen on the
  settings page (stored as UTC, shown in the owner's zone).
- Before the opening time the link shows "opens on ..." with status 200,
  not the 410 of a closed survey.
- Migration: copy `closes_on` into `closes_at` at the end of that day; keep
  the old column for one release, as the add-only rule asks.
- Tests: `tests/test_sharing.py` with a fixed clock.

### 18. Response limit that holds under load

`closed_reason` counts completed responses and compares with
`response_limit`. Two respondents finishing at the same time both pass the
check and both complete, so a limit of 100 can end at 101 or more. With
gunicorn workers that is a real race, not a theoretical one.

- Check and set inside the final submit: lock the survey row
  (`SELECT ... FOR UPDATE` on PostgreSQL) before counting, and refuse the
  completion if the limit is reached. SQLite serialises writes anyway.
- A respondent who loses the race sees the closed page, with their answers
  kept as incomplete.
- Tests: a PostgreSQL only test with two connections; SQLite runs skip it.

### 19. Redirect after the last page

The thank-you page is the end. Owners embedding a survey in their product
want to send people back to the app, or to a coupon page.

- A redirect URL on the settings page, used instead of the thank-you page
  after completion.
- Hidden fields (item 5) can be passed on as query parameters.
- Tricky: open redirects. Only `https://` URLs, set by the owner, never from
  the query string.
- Tests: client tests.

### 20. QR code for the share link

Kiosk mode and event feedback live on paper and screens: a poster at the
door, a slide at the end of a talk.

- A QR code on the sharing panel as SVG and PNG, using a small pure Python
  library (segno), downloadable.
- Tests: a client test that the download is an SVG with the link.

### 21. Excel export

The CSV export already works around spreadsheets (BOM, formula escaping in
`domain/export.py`). An `.xlsx` file avoids the encoding questions
entirely and keeps dates and numbers typed.

- `export.xlsx` next to `export.csv`, with the same columns and filters,
  written with openpyxl in write-only mode so memory stays flat.
- A second sheet with the per question summary.
- Tests: open the file with openpyxl in the test and check a few cells.

### 22. Cross tabulation

Segments compare one choice with everyone. Owners want the full table:
satisfaction by department, NPS by plan.

- Pick two choice questions (or a choice question and a rating) on the
  results page and get counts and row percentages in a table, plus the
  average rating per group.
- A pure function in `domain/results.py` over the answers already loaded
  by `_answers_by_question`.
- CSV download of the table.
- Tests: unit tests with a small fixed data set.

### 23. Shareable results page

Results are visible to the owner only. Sharing them with a team or with the
respondents means screenshots.

- A second token per survey for a read-only results link, off by default,
  that can be revoked.
- Options: hide text answers (they may contain names), hide individual
  responses (always hidden at first).
- Owner pages refuse framing; the shared page may allow it, like the
  public survey pages.
- Tests: client tests for each option and for a revoked token.

### 24. Print-friendly results

Printing the results page or saving it as PDF from the browser prints the
navigation and cuts charts in half.

- A print stylesheet: no navigation and filters, page breaks between
  questions, charts at a fixed width.
- Charts are canvases drawn by Chart.js; they print if they are rendered
  before printing. Check by hand in Firefox and Chromium and note it in the
  PR.
- No test level covers CSS.

### 25. Results computed in the database

`summarize` loads every answer of every completed response into Python
(`_answers_by_question`) and counts there. That is simple and fine for the
demo's 140 responses. With 50,000 responses and twenty questions it is a
million rows per page view, for every filter change.

- Counts per choice, averages and the NPS buckets as `GROUP BY` queries,
  one per question type, that run on SQLite and PostgreSQL alike.
- Medians stay in Python but only fetch the one column they need.
- Text samples are already limited (`TEXT_SAMPLE_SIZE`); query them with a
  limit too.
- A benchmark fixture with generated responses, run by hand, to show the
  before and after.
- Tricky: keep the current tests as the specification. The functions return
  the same `QuestionSummary` objects, so the tests should pass unchanged.

### 26. Automatic cleanup and response retention

`docs/deployment.md` asks operators to run `flask prune-incomplete`
themselves. Most will not. And there is no way to say "delete responses
after a year", which a privacy policy often promises.

- A per survey retention setting (keep forever, or delete completed
  responses after N months).
- One `flask housekeeping` command doing both, and a small loop in the
  container entrypoint (`docker-entrypoint.sh`) that runs it daily, so it
  works without host cron.
- Tests: `tests/test_cli.py` with a fixed clock.

### 27. Sign-in throttling shared by every worker

`LoginThrottle` in `domain/throttle.py` keeps failures in memory per
process. The compose file runs two gunicorn workers by default, so an
attacker gets ten tries per window instead of five, and a restart clears
the count. The README's troubleshooting even suggests restarting to get
unlocked.

- A `login_failures` table (key, time) with the same rules, pruned by the
  housekeeping command of item 26 or on write.
- Keep the class interface so the views do not change.
- Tests: the existing throttle tests against the new store.

### 28. Collaborators on a survey

A survey has one owner (`Survey.owner_id`). A team that shares a survey
shares a password.

- A `survey_members` table with a role: editor (change the survey, see
  results) or viewer (results only).
- `get_owned_survey` becomes `get_survey_for(user, role)`, used by every
  owner route. That is the core of the work and the riskiest part: every
  route in `surveys.py`, `editor.py`, `results.py` and `api.py` has to be
  checked.
- Invitations by email address of an existing account; with item 6, an
  email.
- Tests: a parametrised test that walks every owner route as owner,
  editor, viewer and stranger.

### 29. Respondent pages in other languages

The respondent pages are English only: "Next", "Back", "Required", the
error messages in `domain/answers.py`, the closed and thank-you pages. A
survey written in German still shows English buttons.

- A survey language setting; the respondent pages use it. Flask-Babel for
  the strings, starting with English, German, French and Spanish.
- The owner side stays English for now.
- Tests: a client test per shipped language that a page renders without
  missing strings.

### 30. Accessibility pass on the respondent pages

The respondent pages already use `fieldset` and `legend`, `aria-invalid`
and `aria-describedby`. A focused pass would cover what is left:

- Every input also carries `aria-label="{{ question.prompt }}"`
  (`public/_fields.html`), which repeats the legend for screen readers and
  overrides labels on individual choices.
- After a failed submit, focus should move to an error summary at the top
  that links to each field.
- Rating and NPS scales: check that the radio groups read as a scale with
  their end labels.
- The progress bar has `role="progressbar"` but no accessible name.
- Tests: client tests that assert the markup; a manual pass with a screen
  reader noted in the PR.

### 31. Dark mode

There is one light theme. Respondents opening a link at night get a bright
page, and the accent colour is chosen against white only.

- CSS custom properties with a dark set under
  `prefers-color-scheme: dark`, owner and respondent pages.
- The accent colour needs a contrast check against both backgrounds; pick
  a lighter variant automatically when it fails.
- The contrast check is pure and goes in `domain/` with a unit test.

### 32. Browser tests for the editor

The editor is htmx fragments, and the tests only check the HTML each
request returns. Whether the swaps land in the right place, whether the
CSRF header is sent, and whether the keyboard reorder works are not tested
anywhere.

- Playwright with pytest for a handful of flows: add a question, add
  choices in bulk, reorder, add a skip rule, preview, submit a response.
- A separate CI job against the compose stack, so the main test job stays
  fast.
- Tests: this item is the tests.

## Maybe

### 33. Invitation lists with one-time links

Paste a list of addresses, send each a personal link, see who has not
answered, send a reminder. It turns an anonymous link into a closed panel.
It needs outgoing email (item 6), a recipients table, unsubscribe handling
and bounce awareness, and it ends anonymity for that survey. A lot of new
responsibility for a small tool; hidden fields (item 5) cover the "know who
answered" part when the owner sends links from another tool.

### 34. File upload questions

Uploads mean storage the app does not have today (the deployment notes say
"there are no uploaded files to copy"), virus and type checks, size limits,
and files in the export and in account deletion. Worth it only with a clear
use case; a link question covers some of it.

### 35. Quotas

Close a survey for a group once it has enough answers ("100 per region").
Builds on the race-free limit of item 18 and a choice per quota. Useful for
research panels, rare for feedback forms.

### 36. Multilingual surveys

One survey in several languages, with translated prompts and choices and
results merged across languages. Needs a translation table for every text
column and a language switch on the public page. Item 29 is the cheap first
step.

### 37. Survey versions

Instead of warning about edits (item 1), keep versions: publishing a
changed survey creates a new version, and results can be filtered by it.
The right model for long-running surveys, and a large change to every
query that touches questions.

### 38. Two-factor sign-in

TOTP for owner accounts, with recovery codes. Self-contained (pyotp, a QR
code from item 20). Most useful once collaborators (item 28) make accounts
more valuable.
