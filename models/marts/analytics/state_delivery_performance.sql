-- Where in Brazil is delivery hardest? One row per customer state.
select
    customer_state,
    count(*)                                         as delivered_orders,
    round(avg(days_to_deliver), 1)                   as avg_days_to_deliver,
    round(100.0 * avg(case when is_late then 1.0 else 0.0 end), 1) as late_pct,
    round(avg(review_score), 2)                      as avg_review_score,
    round(100.0 * sum(freight_value) / nullif(sum(items_value), 0), 1) as freight_as_pct_of_items
from {{ ref('fct_orders') }}
where is_delivered
group by customer_state
having count(*) >= 100
order by avg_days_to_deliver desc
