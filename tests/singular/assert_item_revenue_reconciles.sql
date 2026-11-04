-- Total item revenue must be identical in the raw data and in fct_order_items.
with raw as (
    select round(sum(price), 2) as revenue from {{ source('olist', 'olist_order_items_dataset') }}
),
fact as (
    select round(sum(item_price), 2) as revenue from {{ ref('fct_order_items') }}
)
select raw.revenue as raw_revenue, fact.revenue as fact_revenue
from raw, fact
where abs(raw.revenue - fact.revenue) > 0.01
