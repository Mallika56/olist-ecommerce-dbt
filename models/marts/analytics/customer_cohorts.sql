-- Retention: of the people who first bought in month M, what share bought again
-- 1, 2, 3 ... months later? Uses customer_unique_id (the person), not customer_id.
with orders as (
    select customer_unique_id, purchase_month, customer_order_number
    from {{ ref('fct_orders') }}
    where not is_canceled
),
first_month as (
    select customer_unique_id, min(purchase_month) as cohort_month
    from orders group by 1
),
activity as (
    select distinct
        first_month.cohort_month,
        orders.customer_unique_id,
        date_diff('month', first_month.cohort_month, orders.purchase_month) as months_since_first
    from orders
    join first_month using (customer_unique_id)
),
cohort_size as (
    select cohort_month, count(*) as cohort_customers from first_month group by 1
)

select
    activity.cohort_month,
    cohort_size.cohort_customers,
    activity.months_since_first,
    count(*)                                                     as active_customers,
    round(100.0 * count(*) / cohort_size.cohort_customers, 2)    as retention_pct
from activity
join cohort_size using (cohort_month)
group by 1, 2, 3
order by 1, 3
