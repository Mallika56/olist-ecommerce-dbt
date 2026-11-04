-- Business health by month. Revenue = item value of orders not canceled.
with orders as (
    select * from {{ ref('fct_orders') }}
)

select
    purchase_month,
    -- Olist's data starts with a few test-like orders (Sep-Dec 2016) and trails off
    -- after Aug 2018. Trend charts should use complete months only.
    purchase_month between date '{{ var("first_complete_month") }}' and date '{{ var("last_complete_month") }}' as is_complete_month,
    count(*)                                                        as orders,
    count(*) filter (where not is_canceled)                         as completed_orders,
    round(sum(items_value) filter (where not is_canceled), 2)      as revenue,
    round(avg(items_value) filter (where not is_canceled), 2)      as avg_order_value,
    count(distinct customer_unique_id)                              as customers,
    count(*) filter (where customer_order_number = 1)               as first_time_orders,
    count(*) filter (where customer_order_number > 1)               as repeat_orders,
    round(100.0 * avg(case when is_late then 1.0 when is_late = false then 0.0 end), 1) as late_delivery_pct,
    round(avg(review_score), 2)                                     as avg_review_score
from orders
group by purchase_month
order by purchase_month
