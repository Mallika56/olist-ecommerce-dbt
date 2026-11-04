-- One row per product, with the category translated to English.
-- Raw quirks fixed here: misspelled column names ("lenght") and two categories
-- missing from Olist's own translation table.
with products as (
    select * from {{ source('olist', 'olist_products_dataset') }}
),

translation as (
    select * from {{ source('olist', 'product_category_name_translation') }}
)

select
    products.product_id,
    products.product_category_name as category_name_pt,
    coalesce(
        translation.product_category_name_english,
        case products.product_category_name
            when 'pc_gamer' then 'pc_gamer'
            when 'portateis_cozinha_e_preparadores_de_alimentos' then 'portable_kitchen_and_food_preparers'
        end,
        'unknown'
    ) as category,
    products.product_name_lenght        as name_length,
    products.product_description_lenght as description_length,
    products.product_photos_qty          as photo_count,
    products.product_weight_g            as weight_g,
    products.product_length_cm           as length_cm,
    products.product_height_cm           as height_cm,
    products.product_width_cm            as width_cm
from products
left join translation
    on products.product_category_name = translation.product_category_name
