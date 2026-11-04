select
    seller_id,
    lpad(cast(seller_zip_code_prefix as varchar), 5, '0') as zip_code_prefix,
    seller_city  as city,
    upper(seller_state) as state
from {{ source('olist', 'olist_sellers_dataset') }}
