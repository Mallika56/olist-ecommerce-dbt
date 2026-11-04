-- One row per seller with lifetime performance.
with sellers as (
    select * from {{ ref('stg_olist__sellers') }}
),
items as (
    select * from {{ ref('fct_order_items') }} where not is_canceled
),
orders as (
    select order_id, is_late, review_score, days_to_deliver from {{ ref('fct_orders') }}
),
seller_orders as (
    -- One row per (seller, order) so an order with 3 items from a seller counts once.
    select distinct items.seller_id, items.order_id, orders.is_late, orders.review_score, orders.days_to_deliver
    from items
    join orders on items.order_id = orders.order_id
),
item_stats as (
    select
        seller_id,
        count(*)               as items_sold,
        sum(item_price)        as revenue,
        count(distinct category) as categories_sold,
        min(purchased_at)::date as first_sale_date,
        max(purchased_at)::date as last_sale_date
    from items
    group by 1
),
order_stats as (
    select
        seller_id,
        count(*)                             as orders,
        round(avg(case when is_late then 1.0 when is_late = false then 0.0 end), 4) as late_rate,
        round(avg(review_score), 2)          as avg_review_score,
        round(avg(days_to_deliver), 1)       as avg_days_to_deliver
    from seller_orders
    group by 1
)

select
    sellers.seller_id,
    sellers.state,
    sellers.city,
    coalesce(order_stats.orders, 0)     as orders,
    coalesce(item_stats.items_sold, 0)  as items_sold,
    coalesce(item_stats.revenue, 0)     as revenue,
    item_stats.categories_sold,
    item_stats.first_sale_date,
    item_stats.last_sale_date,
    order_stats.late_rate,
    order_stats.avg_review_score,
    order_stats.avg_days_to_deliver
from sellers
left join item_stats  on sellers.seller_id = item_stats.seller_id
left join order_stats on sellers.seller_id = order_stats.seller_id
