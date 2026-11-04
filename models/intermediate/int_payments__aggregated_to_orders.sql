-- Roll payment rows up to one row per order.
-- primary_payment_type = the method that paid the largest share of the order.
with payments as (
    select * from {{ ref('stg_olist__payments') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by order_id order by payment_value desc, payment_number
        ) as value_rank
    from payments
)

select
    order_id,
    sum(payment_value)                               as amount_paid,
    count(*)                                         as payment_count,
    max(case when value_rank = 1 then payment_type end) as primary_payment_type,
    max(installments)                                as max_installments,
    bool_or(payment_type = 'voucher')                as used_voucher
from ranked
group by order_id
