-- One row per zip code prefix.
-- The raw table has ~1M rows (many GPS points per prefix, plus a few outside Brazil).
-- We keep points inside Brazil's bounding box and average them to one centroid.
select
    lpad(cast(geolocation_zip_code_prefix as varchar), 5, '0') as zip_code_prefix,
    avg(geolocation_lat) as latitude,
    avg(geolocation_lng) as longitude,
    count(*)             as source_points
from {{ source('olist', 'olist_geolocation_dataset') }}
where geolocation_lat between -34 and 6
  and geolocation_lng between -74 and -34
group by 1
