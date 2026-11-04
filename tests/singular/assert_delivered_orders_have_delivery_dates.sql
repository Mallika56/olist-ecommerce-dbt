-- An order flagged as delivered must have a delivery timestamp after its purchase.
select order_id, purchased_at, delivered_at
from {{ ref('fct_orders') }}
where is_delivered
  and (delivered_at is null or delivered_at < purchased_at)
