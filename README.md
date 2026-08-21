# Retail Analytics Pipeline

An ETL pipeline that takes one wide, messy retail export (1,000,000 rows × 24 columns),
cleans and normalizes it into a star schema, loads it into PostgreSQL, and produces six
analytics views, five charts, and a written summary report.

**Read the findings:** [`reports/summary_report.md`](reports/summary_report.md)

---

## What it does

```
data/raw/retail_transactions_denormalized.csv     one wide denormalized CSV
              |
              v  extract.py     read, profile, log
              v  transform.py   clean, standardize, quarantine bad rows, normalize
              v  quality.py     18 integrity checks + a referential-integrity gate
              v  load.py        write 6 CSVs, then COPY into PostgreSQL
              v  reports.py     query the views, render 5 PNG charts
              |
              +--> data/processed/*.csv          6 normalized tables
              +--> data/processed/rejected_records/
              +--> reports/charts/*.png          5 charts
              +--> logs/*.log                    one log per module
```

The warehouse is a star schema: four dimensions (`dim_customers`, `dim_products`,
`dim_branches`, `dim_categories`) and two facts (`fact_sales`,
`fact_inventory_snapshot`).

---

## Requirements

- Docker and Docker Compose (this is the supported path — nothing else needs installing)
- Or, for a host-side run: Python 3.10+ and a reachable PostgreSQL 15

---

## Setup

### 1. Clone and add the raw data

The raw CSV is not in the repository — it is supplied separately. Put it here:

```
data/raw/retail_transactions_denormalized.csv
```

The path is hardcoded in `src/main.py`, so the filename must match exactly.

### 2. Check `.env`

`.env` **is committed on purpose** so the project runs on a fresh clone with no extra
setup. It contains:

```
POSTGRES_USER=retail_admin
POSTGRES_PASSWORD=retail_password
POSTGRES_DB=retail_analytics
DB_HOST=db
DB_PORT=5432
```

`DB_HOST=db` and `DB_PORT=5432` are the values that work *inside* the Docker network.
See "Running outside Docker" below if you are not using Compose.

> These are throwaway local credentials. If you reuse this repo with real ones,
> uncomment the `.env` patterns in `.gitignore` first.

---

## Run it

```bash
docker compose up --build
```

That starts PostgreSQL, waits for its healthcheck to pass, then runs the pipeline once
and exits. On a 1M-row input expect a couple of minutes.

The database schema and the six analytics views are applied automatically by Postgres
on **first** startup, from `sql/01_create_schema.sql` and
`sql/02_create_analytics_views.sql` (mounted into `docker-entrypoint-initdb.d`).

### Re-running the pipeline

```bash
docker compose run --rm etl_app
```

The load truncates and reloads all six tables inside a single transaction, so re-running
is safe and repeatable — a failure anywhere rolls back to the previous run's data.

### Connecting to the database

Postgres is published on host port **5433** (not 5432, to avoid clashing with a local
install):

```bash
psql -h localhost -p 5433 -U retail_admin -d retail_analytics
# password: retail_password
```

Or from inside the container:

```bash
docker compose exec db psql -U retail_admin -d retail_analytics
```

### Running the ad-hoc analysis queries

`sql/03_analysis_queries.sql` is not executed by the pipeline. Run it by hand:

```bash
docker compose exec -T db psql -U retail_admin -d retail_analytics < sql/03_analysis_queries.sql
```

---

## Outputs

| Path | What lands there |
|---|---|
| `data/processed/dim_*.csv`, `fact_*.csv` | the six normalized tables (~113 MB total at 1M rows) |
| `data/processed/rejected_records/rejected_records.csv` | rows quarantined during transform, with the reason |
| `data/processed/rejected_records/quality_rejected_records.csv` | rows quarantined by the quality checks (empty on a clean run, so the file may not appear) |
| `reports/charts/*.png` | five charts: daily revenue, top 10 products, revenue by branch, category margin, stockout risk |
| `reports/summary_report.md` | the written findings |
| `logs/*.log` | one log per module — start here when something fails |

These directories are tracked via `.gitkeep` but their contents are gitignored: the CSVs
are too large to commit and the charts are regenerated on every run. An empty
`data/processed/` on a fresh clone is expected, not a missing deliverable.

---

## Analytics views

Defined in `sql/02_create_analytics_views.sql`:

| View | Answers |
|---|---|
| `vw_daily_revenue` | How does revenue change over time? |
| `vw_product_revenue` | Which products generate the most revenue? |
| `vw_branch_revenue` | Which branches have the highest sales? |
| `vw_category_margin` | Which categories are most profitable? |
| `vw_customer_lifetime_value` | Which customers are most valuable? |
| `vw_stockout_risk` | Which products are at risk of stockout? |

---

## Project layout

```
.
├── docker-compose.yml          Postgres 15 + the ETL container
├── Dockerfile                  Python 3.12-slim image for the pipeline
├── .env                        committed local credentials (see above)
├── requirements.txt
├── data/
│   ├── raw/                    put the source CSV here
│   └── processed/              generated tables + rejected records
├── sql/
│   ├── 01_create_schema.sql            star schema DDL, auto-applied on first boot
│   ├── 02_create_analytics_views.sql   6 views, auto-applied on first boot
│   └── 03_analysis_queries.sql         ad-hoc queries, run manually
├── src/
│   ├── main.py                 entry point, wires the five stages together
│   ├── config.py               reads DB settings from the environment
│   ├── extract.py              read + profile the raw CSV
│   ├── transform.py            clean, standardize, quarantine, normalize
│   ├── quality.py              18 checks + assert_referential_integrity()
│   ├── load.py                 write CSVs, COPY into Postgres in one transaction
│   └── reports.py              query the views, render the charts
├── reports/
│   ├── charts/                 five generated PNGs
│   └── summary_report.md       findings
└── logs/                       one log file per module
```

---

## Running outside Docker

Works, but two values in `.env` are wrong for a host-side run — they point at the Docker
network. Override them:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export $(grep -v '^#' .env | xargs)
export DB_HOST=localhost      # .env says "db", which only resolves inside Compose
export DB_PORT=5433           # .env says 5432; that is the container-internal port

python src/main.py
```

`src/main.py` uses relative paths (`./data/raw/...`, `./logs/...`), so run it from the
repository root, not from inside `src/`.

You still need a PostgreSQL 15 with the schema applied. The easiest way is to start just
the database and point the host-side run at it:

```bash
docker compose up -d db
```

Note that `python-dotenv` is in `requirements.txt` but `load_dotenv()` is never called,
which is why `.env` has to be exported manually above.

---

## Troubleshooting

**Schema changes in `sql/01_*.sql` or `sql/02_*.sql` don't take effect.**
`docker-entrypoint-initdb.d` only runs when the data volume is empty. Wipe it and start
over:

```bash
docker compose down -v && docker compose up --build
```

This deletes all loaded data. `01_create_schema.sql` also drops tables without `CASCADE`
and `02` has no `DROP VIEW`, so applying them by hand over an existing schema fails —
the volume reset is the reliable path.

**`could not translate host name "db"`** — you are running on the host with
`DB_HOST=db`. See "Running outside Docker".

**`connection refused` on port 5432** — the host port is 5433. Inside the Docker network
it is 5432.

**`FileNotFoundError: ./data/raw/retail_transactions_denormalized.csv`** — the raw CSV is
missing or renamed. It is not in the repository by design.

**`No such file or directory: './logs/extract.log'`** — you are running from the wrong
directory. Run from the repository root.

**The load failed — are the tables now empty?** No. The truncate and the six loads share
one transaction, so a failure rolls back to the previous run's data. Check `logs/load.log`
for the exception.

---

## Notes on data handling

- **No row is dropped silently.** Everything removed is written to
  `data/processed/rejected_records/` with a reason attached. On the reference dataset
  99.80% of rows are retained.
- **The quality checks run in dependency order.** Any check that can delete a dimension
  row runs before the fact→dimension foreign keys are validated, otherwise it would
  orphan fact rows that had already been cleared. A final
  `assert_referential_integrity()` re-verifies all six foreign-key edges on the finished
  tables and refuses to start the load if an orphan remains — failing there is cheaper
  than a foreign-key violation halfway through a `COPY`.
- **Chart labels are in Persian** and render correctly with the fonts in the image.
