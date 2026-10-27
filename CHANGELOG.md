# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-27

First stable release.

### Surveys and editor

- Seven question types: short text (any, email or number), long text, single
  choice, multiple choice, rating (3 to 10 points), Net Promoter Score and date.
- Required questions plus per-type rules: length limits, number of choices,
  date ranges; options can be shuffled per respondent.
- Pages with titles and intro text; reorder pages and questions, move questions
  between pages, duplicate questions, paste options in bulk.
- Skip logic: jump to a later page or end the survey depending on a choice. Rules
  that would point backwards are removed, and pages nobody can reach are flagged.
- Templates (NPS, event feedback, employee pulse), duplicate a survey, archive.
- Preview a survey without recording anything.

### Sharing and respondents

- Public link per survey with an optional close date (inclusive) and response
  limit; publish, close and reopen keep the same link.
- Anonymous respondents, Back button, progress bar, character counters, numbered
  questions and an estimated completion time.
- Progress is kept for a week; double submits do not create duplicate responses.
- Kiosk mode for several responses per device, accent colour, embeddable pages.

### Results

- Per-question summaries with Chart.js charts, averages and medians.
- Net Promoter Score with promoters, passives, detractors and a monthly trend.
- Responses per day, completion rate and median time to complete.
- Filters by submission date and by answer (segments), compared with everyone.
- Individual responses with next/previous navigation, deleting one or all.
- CSV export (spreadsheet-safe, UTF-8 with BOM) and a read-only JSON API.

### Accounts and operations

- Email and password accounts with throttled sign-in, profile and password
  changes (other devices are signed out), JSON data export, account deletion.
- CSRF protection, security headers and a Content-Security-Policy.
- Docker image and compose setup with PostgreSQL, health checks, request ids in
  logs, demo data, and `flask` commands to seed, create users, export CSV and
  prune abandoned responses.
