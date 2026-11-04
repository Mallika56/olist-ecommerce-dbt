-- Revenue, freight burden and satisfaction by product category.
with items as (
    select * from {{ ref('fct_order_items') }} where not is_canceled
),
orders as (
    select order_id, review_score, is_late from {{ ref('fct_orders') }}
)

select
    items.category,
    count(*)                                                as items_sold,
    count(distinct items.order_id)                          as orders,
    round(sum(items.item_price), 2)                         as revenue,
    round(avg(items.item_price), 2)                         as avg_item_price,
    round(100.0 * sum(items.freight_value) / nullif(sum(items.item_price), 0), 1) as freight_as_pct_of_price,
    round(avg(orders.review_score), 2)                      as avg_review_score,
    round(100.0 * avg(case when orders.is_late then 1.0 when orders.is_late = false then 0.0 end), 1) as late_pct
from items
join orders on items.order_id = orders.order_id
group by items.category
having count(*) >= 200
order by revenue desc
