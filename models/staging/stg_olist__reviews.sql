-- One row per order.
-- Raw quirk: ~550 orders have more than one review row (and some review_ids repeat
-- across orders). We keep the most recently answered review per order so that a
-- review score can be joined to an order without fanning out the row count.
with source as (
    select * from {{ source('olist', 'olist_order_reviews_dataset') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by order_id
            order by review_answer_timestamp desc, review_creation_date desc, review_id
        ) as row_num
    from source
)

select
    review_id,
    order_id,
    review_score,
    nullif(trim(review_comment_title), '')   as review_title,
    nullif(trim(review_comment_message), '') as review_message,
    cast(review_creation_date    as timestamp) as review_sent_at,
    cast(review_answer_timestamp as timestamp) as review_answered_at
from ranked
where row_num = 1
