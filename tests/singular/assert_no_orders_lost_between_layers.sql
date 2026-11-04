-- The fact table must keep every raw order: joins should enrich, never drop or duplicate.
with raw_count as (
    select count(*) as n from {{ source('olist', 'olist_orders_dataset') }}
),
fact_count as (
    select count(*) as n from {{ ref('fct_orders') }}
)
select raw_count.n as raw_orders, fact_count.n as fact_orders
from raw_count, fact_count
where raw_count.n != fact_count.n
