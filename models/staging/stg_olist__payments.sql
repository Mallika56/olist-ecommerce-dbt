-- One row per payment method used on an order.
select
    order_id,
    payment_sequential                       as payment_number,
    order_id || '-' || payment_sequential    as payment_id,
    -- 3 rows are 'not_defined' with a value of 0; keep them but label clearly.
    case when payment_type = 'not_defined' then 'unknown' else payment_type end as payment_type,
    payment_installments                     as installments,
    cast(payment_value as decimal(10, 2))    as payment_value
from {{ source('olist', 'olist_order_payments_dataset') }}
