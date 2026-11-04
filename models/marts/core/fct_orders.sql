-- One row per order: the main table analysts start from.
with orders as (
    select * from {{ ref('stg_olist__orders') }}
),
customers as (
    select * from {{ ref('stg_olist__customers') }}
),
items as (
    select * from {{ ref('int_order_items__aggregated_to_orders') }}
),
payments as (
    select * from {{ ref('int_payments__aggregated_to_orders') }}
),
delivery as (
    select * from {{ ref('int_orders__delivery_metrics') }}
),
reviews as (
    select * from {{ ref('stg_olist__reviews') }}
),

joined as (
    select
        orders.order_id,
        customers.customer_unique_id,
        orders.customer_id,
        customers.state                         as customer_state,
        orders.order_status,
        orders.order_status in ('canceled', 'unavailable') as is_canceled,
        orders.purchased_at,
        cast(orders.purchased_at as date)       as purchase_date,
        date_trunc('month', orders.purchased_at)::date as purchase_month,
        orders.approved_at,
        orders.shipped_at,
        orders.delivered_at,
        orders.estimated_delivery_date,

        coalesce(items.item_count, 0)           as item_count,
        items.distinct_sellers,
        items.items_value,
        items.freight_value,
        items.items_plus_freight,
        payments.amount_paid,
        payments.primary_payment_type,
        payments.max_installments,
        coalesce(payments.used_voucher, false)  as used_voucher,

        delivery.is_delivered,
        delivery.days_to_deliver,
        delivery.days_to_ship,
        delivery.days_in_transit,
        delivery.days_vs_estimate,
        delivery.is_late,
        delivery.delivery_bucket,

        reviews.review_score,
        reviews.review_score is not null        as has_review,
        reviews.review_message is not null      as review_has_comment
    from orders
    left join customers on orders.customer_id = customers.customer_id
    left join items     on orders.order_id = items.order_id
    left join payments  on orders.order_id = payments.order_id
    left join delivery  on orders.order_id = delivery.order_id
    left join reviews   on orders.order_id = reviews.order_id
)

select
    *,
    -- 1 for a person's first order, 2 for their second, ...
    row_number() over (
        partition by customer_unique_id order by purchased_at, order_id
    ) as customer_order_number
from joined
