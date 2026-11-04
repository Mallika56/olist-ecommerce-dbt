-- One row per item sold, with seller-to-customer distance.
with items as (
    select * from {{ ref('stg_olist__order_items') }}
),
orders as (
    select order_id, customer_unique_id, customer_id, purchased_at, order_status, is_canceled
    from {{ ref('fct_orders') }}
),
customers as (
    select customer_id, zip_code_prefix as customer_zip, state as customer_state
    from {{ ref('stg_olist__customers') }}
),
sellers as (
    select seller_id, zip_code_prefix as seller_zip, state as seller_state
    from {{ ref('stg_olist__sellers') }}
),
products as (
    select product_id, category, weight_g from {{ ref('stg_olist__products') }}
),
zips as (
    select * from {{ ref('stg_olist__zip_locations') }}
)

select
    items.order_item_id,
    items.order_id,
    items.order_item_number,
    items.product_id,
    items.seller_id,
    orders.customer_unique_id,
    orders.purchased_at,
    orders.order_status,
    orders.is_canceled,
    products.category,
    products.weight_g,
    items.item_price,
    items.freight_value,
    round(items.freight_value / nullif(items.item_price, 0), 3) as freight_to_price_ratio,
    sellers.seller_state,
    customers.customer_state,
    sellers.seller_state = customers.customer_state as is_same_state,
    -- Straight-line distance between zip-code centroids (haversine, km).
    -- NULL when either zip code has no coordinates in Olist's geolocation table.
    round(
        2 * 6371 * asin(sqrt(
            pow(sin(radians(cz.latitude - sz.latitude) / 2), 2)
            + cos(radians(sz.latitude)) * cos(radians(cz.latitude))
              * pow(sin(radians(cz.longitude - sz.longitude) / 2), 2)
        )), 1
    ) as distance_km
from items
left join orders    on items.order_id = orders.order_id
left join customers on orders.customer_id = customers.customer_id
left join sellers   on items.seller_id = sellers.seller_id
left join products  on items.product_id = products.product_id
left join zips as sz on sellers.seller_zip = sz.zip_code_prefix
left join zips as cz on customers.customer_zip = cz.zip_code_prefix
