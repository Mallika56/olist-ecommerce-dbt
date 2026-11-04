-- Delivery performance per order, measured against the date promised at checkout.
-- Only orders that actually reached the customer get delivery metrics; for others
-- the columns stay NULL rather than pretending to be on time.
with orders as (
    select * from {{ ref('stg_olist__orders') }}
),

delivered as (
    select
        order_id,
        delivered_at is not null and order_status = 'delivered' as is_delivered,
        date_diff('day', purchased_at, delivered_at)            as days_to_deliver,
        date_diff('day', approved_at,  shipped_at)              as days_to_ship,
        date_diff('day', shipped_at,   delivered_at)            as days_in_transit,
        -- Positive = arrived after the promised date; negative = arrived early.
        date_diff('day', estimated_delivery_date, cast(delivered_at as date)) as days_vs_estimate
    from orders
)

select
    order_id,
    is_delivered,
    case when is_delivered then days_to_deliver end  as days_to_deliver,
    case when is_delivered then days_to_ship end     as days_to_ship,
    case when is_delivered then days_in_transit end  as days_in_transit,
    case when is_delivered then days_vs_estimate end as days_vs_estimate,
    case when is_delivered then days_vs_estimate > {{ var('late_grace_days') }} end as is_late,
    case
        when not is_delivered            then null
        when days_vs_estimate <= -10     then '1. 10+ days early'
        when days_vs_estimate <= -1      then '2. 1-9 days early'
        when days_vs_estimate = 0        then '3. on the day'
        when days_vs_estimate <= 3       then '4. 1-3 days late'
        when days_vs_estimate <= 7       then '5. 4-7 days late'
        when days_vs_estimate <= 14      then '6. 8-14 days late'
        else                                  '7. 15+ days late'
    end as delivery_bucket
from delivered
