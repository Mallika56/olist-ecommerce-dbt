-- One row per order-level customer record.
-- customer_id changes on every order; customer_unique_id is the real person.
select
    customer_id,
    customer_unique_id,
    lpad(cast(customer_zip_code_prefix as varchar), 5, '0') as zip_code_prefix,
    customer_city  as city,
    upper(customer_state) as state
from {{ source('olist', 'olist_customers_dataset') }}
