select
    product_id,
    category,
    category_name_pt,
    photo_count,
    weight_g,
    length_cm,
    height_cm,
    width_cm,
    length_cm * height_cm * width_cm as volume_cm3
from {{ ref('stg_olist__products') }}
