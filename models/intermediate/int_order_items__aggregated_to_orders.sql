-- Roll item lines up to one row per order.
select
    order_id,
    count(*)                          as item_count,
    count(distinct product_id)        as distinct_products,
    count(distinct seller_id)         as distinct_sellers,
    sum(item_price)                   as items_value,
    sum(freight_value)                as freight_value,
    sum(item_price) + sum(freight_value) as items_plus_freight
from {{ ref('stg_olist__order_items') }}
group by order_id
