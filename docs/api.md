# JSON API

A small, read-only API for scripts and dashboards. It uses the same session
cookie as the web app, so sign in first (for example with `curl -c cookies.txt`
against `/login`). Every endpoint only returns surveys owned by the signed-in
user.

Errors are JSON objects with an `error` key:

| Status | Body                                  | When                          |
| ------ | ------------------------------------- | ----------------------------- |
| 401    | `{"error": "authentication required"}` | No session                    |
| 404    | `{"error": "not found"}`              | Unknown or someone else's survey |

## `GET /api/surveys`

```json
{
  "surveys": [
    {
      "id": 1,
      "title": "Customer satisfaction 2026",
      "status": "published",
      "share_token": "f3N1c2n0bWVyLXNh",
      "closes_on": null,
      "response_limit": 500,
      "created_at": "2026-01-10T11:50:10Z"
    }
  ]
}
```

`status` is one of `draft`, `published` or `closed`. The public link of a
survey is `/s/<share_token>`.

## `GET /api/surveys/<id>/summary`

Optional query parameters `from` and `to` (`YYYY-MM-DD`, inclusive, UTC) limit
the summary to responses submitted in that period.

```json
{
  "survey": { "id": 1, "title": "Customer satisfaction 2026", "...": "..." },
  "responses": {
    "completed": 140,
    "started": 171,
    "completion_rate": 82,
    "median_seconds": 254
  },
  "questions": [
    {
      "id": 3,
      "type": "single_choice",
      "prompt": "Which plan are you on?",
      "answered": 140,
      "labels": ["Free", "Starter", "Business", "Enterprise"],
      "counts": [61, 40, 27, 12]
    },
    {
      "id": 7,
      "type": "nps",
      "prompt": "How likely are you to recommend us?",
      "answered": 140,
      "labels": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
      "counts": [3, 2, 4, 3, 2, 4, 6, 15, 27, 34, 40],
      "average": 7.6,
      "nps": { "score": 35, "promoters": 74, "passives": 42, "detractors": 24 }
    }
  ]
}
```

- Choice, rating and NPS questions include `labels` and `counts` in display order.
- Rating and NPS questions include `average`; NPS questions also include `nps`.
- Text questions only report how many people `answered`. Use the CSV export
  (`/surveys/<id>/results/export.csv`) for the answers themselves.

## `GET /api/surveys/<id>/responses`

Completed responses, oldest first. Query parameters:

| Parameter  | Default | Notes                                        |
| ---------- | ------- | -------------------------------------------- |
| `page`     | `1`     | Out of range values are clamped               |
| `per_page` | `50`    | 1 to 200                                      |
| `from`, `to` | —     | Same date filter as the summary               |
| `choice`   | —       | Only respondents who picked this choice id    |

```json
{
  "responses": [
    {
      "id": 412,
      "completed_at": "2026-07-21T18:03:11Z",
      "answers": {
        "3": "Business",
        "4": ["Dashboards", "CSV export"],
        "5": "2024-03-01",
        "6": 4,
        "7": 9,
        "8": null
      }
    }
  ],
  "page": 1,
  "pages": 3,
  "total": 140
}
```

`answers` is keyed by question id (as a string). Values are the choice label,
a list of labels for multiple choice, a number for rating and NPS, an ISO date
or the text. Unanswered questions are `null`.
