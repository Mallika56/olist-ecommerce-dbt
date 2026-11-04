-- One row per item line. order_item_id is the line number inside the order (1, 2, 3...).
select
    order_id,
    order_item_id                         as order_item_number,
    order_id || '-' || order_item_id      as order_item_id,   -- surrogate key for the grain
    product_id,
    seller_id,
    cast(shipping_limit_date as timestamp) as seller_ship_by_at,
    cast(price         as decimal(10, 2))  as item_price,
    cast(freight_value as decimal(10, 2))  as freight_value
from {{ source('olist', 'olist_order_items_dataset') }}
