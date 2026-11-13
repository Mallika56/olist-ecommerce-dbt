"""Query the dbt marts and produce the README results + charts.

    dbt build --profiles-dir .
    python scripts/run_analysis.py

Writes docs/results/*.csv, docs/results/headline_numbers.json and docs/img/*.png.
Every number in the README comes from this script.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "olist.duckdb"
RES = ROOT / "docs/results"
IMG = ROOT / "docs/img"

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
BLUE, ORANGE = "#2a78d6", "#eb6834"

CHART_STYLE = {
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "axes.axisbelow": True,
}

MART_TABLES = ["delivery_vs_reviews", "monthly_kpis", "state_delivery_performance",
               "seller_scorecard", "category_performance"]


def connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Open a read-only connection to the dbt-built DuckDB warehouse."""
    return duckdb.connect(str(db_path), read_only=True)


def query(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    """Run a SQL statement against the warehouse and return it as a DataFrame."""
    return con.execute(sql).df()


def write_mart_tables(con: duckdb.DuckDBPyConnection, res_dir: Path) -> None:
    """Dump each analytics mart referenced directly in the README to its own CSV."""
    for table in MART_TABLES:
        query(con, f"select * from analytics.{table}").to_csv(res_dir / f"{table}.csv", index=False)


def compute_retention(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Weighted month-1..12 retention across cohorts with 6+ months of follow-up."""
    return query(con, """
        select months_since_first,
               round(100.0 * sum(active_customers) / sum(cohort_customers), 2) as retention_pct
        from analytics.customer_cohorts
        where months_since_first between 1 and 12
          and cohort_month between date '2017-01-01' and date '2018-02-01'  -- cohorts with 6+ months of follow-up
        group by 1 order by 1
    """)


def compute_headline_numbers(con: duckdb.DuckDBPyConnection, retention: pd.DataFrame) -> dict:
    """Build the headline_numbers dict that drives every number quoted in the README."""
    h = {}
    h["orders"] = int(query(con, "select count(*) n from core.fct_orders").n[0])
    h["items"] = int(query(con, "select count(*) n from core.fct_order_items").n[0])
    h["customers"] = int(query(con, "select count(*) n from core.dim_customers").n[0])
    h["sellers"] = int(query(con, "select count(*) n from core.dim_sellers").n[0])
    d = query(con, """select count(*) delivered,
                    round(100 * avg(case when is_late then 1.0 else 0 end), 1) late_pct,
                    median(days_vs_estimate) median_days_vs_estimate,
                    round(median(days_to_deliver), 1) median_days_to_deliver
             from core.fct_orders where is_delivered""")
    h.update({k: (float(v) if k != "delivered" else int(v)) for k, v in d.iloc[0].items()})
    r = query(con, """select round(avg(review_score) filter (where is_late), 2) late_avg,
                    round(avg(review_score) filter (where not is_late), 2) on_time_avg,
                    round(100 * avg(case when review_score = 1 then 1.0 else 0 end) filter (where is_late), 1) late_one_star_pct,
                    round(100 * avg(case when review_score = 1 then 1.0 else 0 end) filter (where not is_late), 1) on_time_one_star_pct
             from core.fct_orders where is_delivered and has_review""")
    h.update({k: float(v) for k, v in r.iloc[0].items()})
    c = query(con, "select count(*) n, round(100 * avg(is_repeat_customer::int), 2) repeat_pct from core.dim_customers")
    h["repeat_customer_pct"] = float(c.repeat_pct[0])
    h["month1_retention_pct"] = float(retention.retention_pct[0])
    s = query(con, """select i.is_same_state,
                    round(avg(o.days_to_deliver), 1) avg_days,
                    round(100 * avg(case when o.is_late then 1.0 else 0 end), 1) late_pct,
                    count(distinct o.order_id) orders
             from core.fct_order_items i join core.fct_orders o using (order_id)
             where o.is_delivered group by 1""").set_index("is_same_state")
    h["same_state_avg_days"] = float(s.loc[True, "avg_days"])
    h["cross_state_avg_days"] = float(s.loc[False, "avg_days"])
    h["same_state_late_pct"] = float(s.loc[True, "late_pct"])
    h["cross_state_late_pct"] = float(s.loc[False, "late_pct"])
    peak = query(con, """select purchase_month, late_delivery_pct, avg_review_score
                from analytics.monthly_kpis where is_complete_month order by late_delivery_pct desc limit 3""")
    h["worst_late_months"] = [
        {"month": str(m)[:7], "late_pct": float(lp), "avg_review": float(ar)}
        for m, lp, ar in peak.itertuples(index=False)
    ]
    tiers = query(con, "select tier, count(*) n from analytics.seller_scorecard group by 1")
    h["seller_tiers"] = dict(zip(tiers.tier, map(int, tiers.n)))
    return h


def make_review_vs_delivery_chart(con: duckdb.DuckDBPyConnection, img_dir: Path) -> None:
    """Bar chart: average review score by delivery-timing bucket."""
    dv = query(con, "select * from analytics.delivery_vs_reviews order by delivery_bucket")
    labels = [b.split(". ", 1)[1] for b in dv.delivery_bucket]
    colors = [BLUE if "early" in b or "on the day" in b else ORANGE for b in dv.delivery_bucket]
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(labels, dv.avg_review_score, color=colors, width=0.62)
    for b, v, n in zip(bars, dv.avg_review_score, dv.orders):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.06, f"{v:.2f}", ha="center", color=INK, fontsize=10)
        ax.text(b.get_x() + b.get_width() / 2, 0.12, f"{n:,} orders", ha="center", color="white", fontsize=8)
    ax.set_ylim(0, 5)
    ax.set_ylabel("Average review (1-5 stars)")
    ax.grid(axis="x", visible=False)
    ax.legend(handles=[Patch(color=BLUE, label="on time or early"), Patch(color=ORANGE, label="late")],
              frameon=False, loc="upper right")
    ax.set_title("Arriving even 1-3 days late drops the average review from 4.0+ to 3.3",
                 loc="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(img_dir / "delivery_vs_reviews.png", dpi=160)


def make_monthly_trend_chart(con: duckdb.DuckDBPyConnection, img_dir: Path) -> None:
    """Two-panel chart: monthly order volume and late-delivery rate."""
    mk = query(con, "select * from analytics.monthly_kpis where is_complete_month order by purchase_month")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 5.2), sharex=True, height_ratios=[1.2, 1])
    a1.plot(mk.purchase_month, mk.orders, color=BLUE, lw=2)
    a1.set_ylabel("Orders")
    a1.set_title("Order volume grew fast; late deliveries spiked in Nov 2017 (Black Friday) and Feb-Mar 2018",
                 loc="left", fontsize=12, fontweight="bold")
    a2.plot(mk.purchase_month, mk.late_delivery_pct, color=ORANGE, lw=2)
    a2.set_ylabel("% delivered late")
    for _, row in mk.nlargest(2, "late_delivery_pct").iterrows():
        a2.annotate(f"{row.late_delivery_pct:.0f}%", (row.purchase_month, row.late_delivery_pct),
                    xytext=(6, 0), textcoords="offset points", color=INK2, va="center")
    fig.tight_layout()
    fig.savefig(img_dir / "monthly_trend.png", dpi=160)


def make_state_delivery_chart(con: duckdb.DuckDBPyConnection, img_dir: Path) -> float:
    """Scatter chart: state-level delivery speed vs review score. Returns the correlation."""
    st = query(con, "select * from analytics.state_delivery_performance")
    r_state = float(st.avg_days_to_deliver.corr(st.avg_review_score))
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.scatter(st.avg_days_to_deliver, st.avg_review_score, s=st.delivered_orders.clip(upper=12000) / 25 + 25,
               color=BLUE, alpha=0.75, edgecolor=SURFACE, linewidth=1.5)
    for _, row in st.iterrows():
        if row.customer_state in {"SP", "RJ", "MG", "AL", "MA", "AM", "RR", "AP", "PR", "BA", "CE"}:
            ax.annotate(row.customer_state, (row.avg_days_to_deliver, row.avg_review_score),
                        xytext=(0, 13), textcoords="offset points", color=INK2, ha="center", fontsize=9)
    ax.set_ylim(top=st.avg_review_score.max() + 0.06)
    ax.set_xlabel("Average days from purchase to delivery")
    ax.set_ylabel("Average review")
    ax.set_title(f"States with slower delivery rate lower (r = {r_state:.2f}); Amazonas (AM) is the exception",
                 loc="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(img_dir / "state_delivery.png", dpi=160)
    return round(r_state, 2)


def main() -> None:
    """Build the warehouse connection, write the mart CSVs/charts, and save headline_numbers.json."""
    RES.mkdir(parents=True, exist_ok=True)
    IMG.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(CHART_STYLE)

    con = connect(DB_PATH)

    write_mart_tables(con, RES)
    retention = compute_retention(con)
    retention.to_csv(RES / "retention_by_month_weighted.csv", index=False)

    h = compute_headline_numbers(con, retention)

    make_review_vs_delivery_chart(con, IMG)
    make_monthly_trend_chart(con, IMG)
    h["state_days_review_correlation"] = make_state_delivery_chart(con, IMG)

    (RES / "headline_numbers.json").write_text(json.dumps(h, indent=2, default=str))
    print(json.dumps(h, indent=2, default=str))
    print("charts written to", IMG)


if __name__ == "__main__":
    main()
