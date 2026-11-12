"""Unit tests for scripts/run_analysis.py against an in-memory DuckDB fixture.

No network access and no dependency on a real dbt build -- the fixture creates
just enough rows in each mart/core table to exercise the real SQL and chart code.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_analysis as ra


@pytest.fixture()
def con():
    con = duckdb.connect(":memory:")
    con.execute("create schema core")
    con.execute("create schema analytics")

    con.execute("""
        create table core.fct_orders as select * from (values
            (1, true,  false, -2, 5, true,  5),
            (2, true,  true,   3, 9, true,  1),
            (3, true,  false, -1, 6, false, null),
            (4, false, false, null, null, false, null)
        ) as t(order_id, is_delivered, is_late, days_vs_estimate, days_to_deliver,
               has_review, review_score)
    """)
    con.execute("""
        create table core.fct_order_items as select * from (values
            (1, true), (2, false), (3, true)
        ) as t(order_id, is_same_state)
    """)
    con.execute("""
        create table core.dim_customers as select * from (values
            (1, true), (2, false), (3, false)
        ) as t(customer_id, is_repeat_customer)
    """)
    con.execute("create table core.dim_sellers as select * from (values (1), (2)) as t(seller_id)")

    con.execute("""
        create table analytics.delivery_vs_reviews as select * from (values
            ('1. early', 4.3, 120), ('2. late', 3.3, 40)
        ) as t(delivery_bucket, avg_review_score, orders)
    """)
    con.execute("""
        create table analytics.monthly_kpis as select * from (values
            (date '2017-11-01', 10.0, 4.0, 500, true),
            (date '2017-12-01', 25.0, 3.7, 600, true),
            (date '2018-03-01', 99.0, 1.0, 10,  false)
        ) as t(purchase_month, late_delivery_pct, avg_review_score, orders, is_complete_month)
    """)
    con.execute("""
        create table analytics.state_delivery_performance as select * from (values
            ('SP', 8.0, 4.2, 9000), ('AM', 25.0, 4.5, 50), ('RR', 22.0, 3.1, 40)
        ) as t(customer_state, avg_days_to_deliver, avg_review_score, delivered_orders)
    """)
    con.execute("""
        create table analytics.category_performance as select * from (values (1,)) as t(n)
    """)
    con.execute("""
        create table analytics.seller_scorecard as select * from (values
            ('gold', 1), ('gold', 2), ('silver', 3)
        ) as t(tier, seller_id)
    """)
    con.execute("""
        create table analytics.customer_cohorts as select * from (values
            (date '2017-01-01', 1, 100, 80),
            (date '2017-02-01', 1, 90,  60)
        ) as t(cohort_month, months_since_first, cohort_customers, active_customers)
    """)
    return con


def test_write_mart_tables_writes_one_csv_per_mart(con, tmp_path):
    ra.write_mart_tables(con, tmp_path)
    for table in ra.MART_TABLES:
        assert (tmp_path / f"{table}.csv").exists()


def test_compute_retention_weights_by_cohort_size(con):
    retention = ra.compute_retention(con)
    assert retention.months_since_first.tolist() == [1]
    assert retention.retention_pct[0] == pytest.approx(100.0 * (80 + 60) / (100 + 90), abs=0.01)


def test_compute_headline_numbers_matches_expected_counts(con):
    retention = ra.compute_retention(con)
    h = ra.compute_headline_numbers(con, retention)
    assert h["orders"] == 4
    assert h["customers"] == 3
    assert h["sellers"] == 2
    assert h["delivered"] == 3
    assert h["same_state_avg_days"] == pytest.approx((5 + 6) / 2, abs=0.01)
    assert h["cross_state_avg_days"] == pytest.approx(9.0, abs=0.01)
    assert h["seller_tiers"] == {"gold": 2, "silver": 1}


def test_make_review_vs_delivery_chart_writes_png(con, tmp_path):
    ra.make_review_vs_delivery_chart(con, tmp_path)
    assert (tmp_path / "delivery_vs_reviews.png").exists()


def test_make_monthly_trend_chart_writes_png(con, tmp_path):
    ra.make_monthly_trend_chart(con, tmp_path)
    assert (tmp_path / "monthly_trend.png").exists()


def test_make_state_delivery_chart_returns_correlation_and_writes_png(con, tmp_path):
    corr = ra.make_state_delivery_chart(con, tmp_path)
    assert (tmp_path / "state_delivery.png").exists()
    assert isinstance(corr, float)
    assert -1.0 <= corr <= 1.0


def test_main_writes_headline_json_with_state_correlation(con, tmp_path, monkeypatch):
    monkeypatch.setattr(ra, "connect", lambda _db_path: con)
    monkeypatch.setattr(ra, "RES", tmp_path)
    monkeypatch.setattr(ra, "IMG", tmp_path)

    ra.main()

    headline = json.loads((tmp_path / "headline_numbers.json").read_text())
    assert "state_days_review_correlation" in headline
    assert headline["orders"] == 4
