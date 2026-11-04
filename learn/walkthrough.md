# Walkthrough: Olist dbt project

This guide starts from zero. Plan on **4–5 hours**:

| Session | What | Time |
|---|---|---|
| 1 | Parts 1–3: what dbt is, vocabulary, the data | 1 hr |
| 2 | Part 4: run it, then read the models layer by layer | 1.5–2 hrs |
| 3 | Part 5: tests and docs | 45 min |
| 4 | Parts 6–7: exercises + interview answers out loud | 1 hr |

---

## Part 1: What dbt is (and isn't)

**dbt (data build tool) is the "T" in ELT.** Data is first *loaded* into a warehouse (here: CSVs read by
DuckDB), then dbt *transforms* it using plain `SELECT` statements.

Each `.sql` file in `models/` is one `SELECT`. dbt:

1. figures out the order to build them (from `{{ ref('...') }}`), which gives you the **lineage graph**
2. wraps each SELECT in `CREATE VIEW` or `CREATE TABLE` (the **materialization**)
3. runs **tests** you declare in YAML
4. generates a **documentation website** from your descriptions

What dbt is *not*: it doesn't move data between systems (that's Fivetran/Airbyte/a Python script) and
it doesn't schedule itself (that's Airflow, dbt Cloud or cron).

**Your 30-second pitch:**
> "I built an analytics-engineering project on Olist's 100k real e-commerce orders using dbt and DuckDB.
> I modeled raw CSVs through staging, intermediate and mart layers into a star schema, with two fact tables
> at different grains and four dimensions. It has 81 data tests, two dbt unit tests, and CI on GitHub Actions.
> Then I used the marts to show that late deliveries are under 7% of orders but a third of all bad reviews,
> and turned that into recommendations about peak-season capacity and seller performance."

---

## Part 2: Vocabulary

| Term | Meaning | Here |
|---|---|---|
| **Model** | One SELECT statement saved as a `.sql` file | `fct_orders.sql` |
| **`ref()`** | How a model points at another model. dbt uses it to build the dependency graph | `{{ ref('stg_olist__orders') }}` |
| **`source()`** | How a model points at raw data | `{{ source('olist', 'olist_orders_dataset') }}` |
| **Materialization** | View (re-runs the query each time, no storage) or table (stores results, fast to query) | Staging and intermediate = views; marts = tables |
| **Staging layer** | 1:1 with a source. Clean names and types, nothing else | `stg_olist__*` |
| **Intermediate layer** | Reusable business logic that several marts need | `int_orders__delivery_metrics` |
| **Mart** | Final tables people query | `fct_orders`, `monthly_kpis` |
| **Fact table** | Events or transactions; many rows; numeric measures | `fct_orders` (one row per order) |
| **Dimension** | Descriptive "who/what/when" | `dim_customers`, `dim_dates` |
| **Star schema** | Facts in the middle, dimensions around them, joined by keys | the core marts |
| **Grain** | What ONE row represents. The most important design decision | order vs order item |
| **Data test** | A query that returns the *bad* rows; 0 rows = pass | `unique`, `not_null`, singular tests |
| **Unit test** | Fixed fake input → expected output, to test *logic* not data | delivery classification |
| **Exposure** | Documents what *uses* the models (a dashboard, an analysis) | `olist_ops_insights` |

---

## Part 3: The data, and why it's tricky

Nine CSVs from a real marketplace. The traps (each is a great interview story):

1. **`customer_id` ≠ customer.** Olist creates a new `customer_id` for every order. The real person is
   `customer_unique_id`. Count `customer_id` and you'd conclude nobody ever returns (or overcount customers).
2. **Duplicate reviews.** 547 orders have more than one review row. Join reviews to orders naively and those
   orders appear twice, so revenue is double-counted.
3. **Two grains.** `orders` has one row per order; `order_items` has one row per item. Mixing them in one
   SUM is the classic "fan-out" bug.
4. **Payments split across methods** (voucher + card), and **instalment interest** makes the paid amount
   higher than the order total.

---

## Part 4: Run it and read it

```bash
pip install -r requirements.txt
python scripts/download_data.py
dbt build --profiles-dir .
python scripts/run_analysis.py
dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .   # opens a website
```

In the docs site, click the blue graph icon (bottom right) to see the lineage.

### Config files
* `dbt_project.yml`: project settings. The `models:` block makes staging and intermediate **views** and marts
  **tables**, and gives each folder its own schema. `vars:` holds settings like `as_of_date`.
* `profiles.yml`: *where* to run. Here a DuckDB file; for Snowflake you'd only change this file.
* `macros/generate_schema_name.sql`: by default dbt names schemas `main_staging`; this override keeps them
  clean (`staging`, `core`, `analytics`).

### Staging: `models/staging/`
* `_sources.yml` declares the raw tables. The `external_location` line is dbt-duckdb's way of reading CSV
  files directly: `{name}` becomes each table's name.
* `stg_olist__orders.sql`: only renames and casts. `order_purchase_timestamp` → `purchased_at`.
  **Why so boring?** Staging is the one place that knows about raw quirks. If Olist renames a column,
  you fix it in one file.
* `stg_olist__reviews.sql`: the dedup. Read it carefully:
  ```sql
  row_number() over (partition by order_id order by review_answer_timestamp desc, ...) as row_num
  ...
  where row_num = 1
  ```
  "For each order, number its reviews newest first, keep #1." This is the most common SQL interview
  pattern there is.
* `stg_olist__zip_locations.sql`: 1M GPS points → one average point per zip, after dropping points
  outside Brazil's latitude/longitude box.

### Intermediate: `models/intermediate/`
* `int_orders__delivery_metrics.sql`: the business rule. `days_vs_estimate` = delivered date minus promised
  date. **Key design choice:** for orders that never arrived, every metric is `NULL`, not 0 or FALSE.
  Otherwise a canceled order would count as "on time" and flatter the late rate.
* `int_payments__aggregated_to_orders.sql`: one row per order. `primary_payment_type` uses
  `row_number()` ordered by payment value, so the biggest payment wins.
* `int_order_items__aggregated_to_orders.sql`: rolls items up to orders **before** joining, which avoids
  fan-out.

### Core marts: `models/marts/core/`
* `fct_orders.sql`: CTEs for each input, then left joins on `order_id`. Every input is already one row per
  order, so the join can't multiply rows. A singular test proves it: raw order count = fact order count.
  `customer_order_number` (1st, 2nd... order for that person) powers new-vs-repeat analysis.
* `fct_order_items.sql`: item grain. Adds the **haversine** distance between seller and customer zip centroids.
* `dim_customers.sql`: grouped by `customer_unique_id`. Uses `filter (where ...)` (conditional aggregation)
  and `qualify` (filter on a window function without a subquery).
* `dim_sellers.sql`: counts orders **once per seller** using `select distinct seller_id, order_id`. A
  seller with 3 items in one order still has one late order, not three.

### Analytics marts: `models/marts/analytics/`
Answer-shaped tables, so a dashboard needs no complex SQL. Look at:
* `delivery_vs_reviews.sql`: `count(*) / sum(count(*)) over ()` = percent of total in one query.
* `customer_cohorts.sql`: classic cohort retention with `date_diff('month', ...)`.

---

## Part 5: Tests and documentation

Open `models/staging/_staging.yml` and `models/intermediate/_intermediate.yml`.

* **Generic tests** are one-liners: `data_tests: [unique, not_null]`. dbt generates a query that returns
  violating rows.
* **`relationships`** = foreign-key check: every `order_id` in items must exist in orders.
* **`tests/generic/positive_value.sql`**: your own reusable test with a parameter (`allow_zero`).
* **Singular tests** (`tests/singular/`) are plain SELECTs returning bad rows. The best ones *reconcile*:
  raw revenue = fact revenue.
* **The payment test is set to `warn`**, not fail. It first flagged 247 orders. Investigation showed 227 were
  credit-card instalments with interest, which is legitimate. Those are excluded; the remaining 20 are real
  oddities in Olist's data, so a warning is the honest setting. *This is a great story about not blindly
  trusting a failing test.*
* **Unit tests** (bottom of `_intermediate.yml`): fake rows in, expected rows out. They test the *logic*
  (is a 5-days-late order bucketed "4–7 days late"?) independently of the real data.

---

## Part 6: Try it yourself

1. **New mart:** `payment_mix.sql`, showing revenue and average instalments by `primary_payment_type`. Add a
   `unique` test on payment type. Run `dbt build --select payment_mix`.
2. **Break a test on purpose.** In `stg_olist__reviews.sql`, delete `where row_num = 1`. Run `dbt build`.
   Which tests fail, and how many extra rows appear in `fct_orders`? Put it back.
3. **Change a business rule.** Set `late_grace_days: 1` in `dbt_project.yml`. Rebuild. How does the late
   rate change? Why might a company choose a grace day?
4. **Write a unit test** for `stg_olist__products`: a product with category `pc_gamer` should get
   `category = 'pc_gamer'`.
5. **Selectors:** run `dbt build --select +fct_orders` (fct_orders and everything upstream) and
   `dbt build --select fct_orders+` (and everything downstream). Explain the difference.

---

## Part 7: Interview questions

**1. Why staging → intermediate → marts?**
Separation of concerns. Staging isolates raw-data quirks (rename and type once). Intermediate holds
reusable logic (the late-delivery rule is defined in one place). Marts are shaped for consumers. When a
source changes, I fix one staging model and everything downstream keeps working.

**2. View or table? How did you decide?**
Staging and intermediate are views: they're cheap and always current, and only dbt reads them. Marts are
tables because people and dashboards query them repeatedly, so precomputing is faster. At larger scale I'd
make `fct_orders` incremental.

**3. What is grain, and how did you handle multiple grains?**
Grain is what one row represents. Orders and order items are different grains, so I built two facts. I
aggregated items and payments up to the order level *before* joining, which prevents the fan-out where an
order with 3 items gets its payment counted 3 times. A singular test confirms the fact has exactly one row
per raw order.

**4. How do you know your data is right?**
81 data tests: keys are unique and not null, foreign keys exist, values are in allowed sets. Plus
reconciliation tests between layers (no orders lost, revenue matches raw to the cent) and unit tests on the
delivery rule. CI runs all of it on every push.

**5. Tell me about a data-quality issue you found.**
The payment reconciliation test flagged 247 orders where the amount paid didn't match the order total. I
investigated before "fixing" anything. 227 were credit-card orders split into instalments, where Brazilian
cards add interest, so the customer legitimately paid more. I encoded that rule, and the remaining 20
(0.02%) are genuine source anomalies, so the test warns instead of failing.

**6. customer_id vs customer_unique_id?**
Olist issues a new customer_id per order. Counting it would say there are 99k customers and nobody repeats.
The real person is customer_unique_id: 96k people, 3% repeat. All customer metrics use it.

**7. How would this run in production?**
Swap `profiles.yml` to Snowflake or BigQuery. Schedule `dbt build` with Airflow or dbt Cloud after the
daily load. Make the big facts incremental, add source freshness checks, and snapshot slowly changing
dimensions such as seller attributes.

**8. What did you find, and what would you recommend?**
Late orders are 6.7% of deliveries but 32.5% of 1–2 star reviews (2.27 stars vs 4.29 on time). Late rates
tripled around Black Friday and in Feb–Mar 2018. Same-state shipments arrive in about half the time.
Recommendations: make "late" the core ops KPI, add capacity before peaks, manage the 89 at-risk sellers,
and work on retention, since only 3% of customers return.

---

## Resume bullets (pick 2)

- Built a dbt + DuckDB analytics-engineering project on 99k real Olist e-commerce orders, modeling 9 raw sources
  into a star schema (2 facts, 4 dimensions) across staging, intermediate and mart layers
- Implemented 81 data tests, 2 dbt unit tests and layer-to-layer reconciliation checks with GitHub Actions CI;
  investigated a payment mismatch down to instalment interest and encoded the business rule
- Showed that late deliveries (6.7% of orders) drive 32.5% of 1–2 star reviews and spike 3× in peak season;
  recommended peak capacity planning and a seller performance program using a tiered seller scorecard
