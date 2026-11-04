-- One row per real person (customer_unique_id), not per order.
with orders as (
    select * from {{ ref('fct_orders') }}
),
latest_location as (
    select customer_unique_id, customer_state
    from orders
    qualify row_number() over (partition by customer_unique_id order by purchased_at desc) = 1
)

select
    orders.customer_unique_id,
    latest_location.customer_state                           as state,
    min(orders.purchase_date)                                as first_order_date,
    max(orders.purchase_date)                                as last_order_date,
    count(*)                                                 as order_count,
    count(*) filter (where not orders.is_canceled)           as completed_order_count,
    sum(orders.items_value) filter (where not orders.is_canceled) as lifetime_items_value,
    count(*) filter (where not orders.is_canceled) > 1       as is_repeat_customer,
    round(avg(orders.review_score), 2)                       as avg_review_score,
    date_diff('day', max(orders.purchase_date), date '{{ var("as_of_date") }}') as days_since_last_order
from orders
left join latest_location using (customer_unique_id)
group by 1, 2
