-- trips_clean: one row per usable yellow taxi trip, Jul-Sep 2026, with zone names and derived fields.
-- Every filter below is counted in 00_data_checks.sql so the rows removed are documented.

DROP VIEW IF EXISTS trips_clean;
CREATE VIEW trips_clean AS
SELECT
    t.pickup_at,
    t.dropoff_at,
    t.pickup_at::date                                          AS pickup_date,
    EXTRACT(HOUR FROM t.pickup_at)::int                        AS pickup_hour,
    EXTRACT(ISODOW FROM t.pickup_at)::int                      AS iso_dow,   -- 1 = Monday ... 7 = Sunday
    EXTRACT(ISODOW FROM t.pickup_at) IN (6, 7)                 AS is_weekend,
    EXTRACT(EPOCH FROM (t.dropoff_at - t.pickup_at)) / 60.0    AS duration_min,
    t.trip_distance,
    t.trip_distance / (EXTRACT(EPOCH FROM (t.dropoff_at - t.pickup_at)) / 3600.0) AS avg_mph,
    t.passenger_count,
    t.payment_type,
    t.fare_amount,
    t.tip_amount,
    t.total_amount,
    pu.borough                                                 AS pu_borough,
    pu.zone                                                    AS pu_zone,
    dz.borough                                                 AS do_borough,
    dz.zone                                                    AS do_zone,
    (pu.zone ILIKE '%Airport%' OR dz.zone ILIKE '%Airport%')   AS is_airport_trip
FROM trips_raw t
JOIN zones pu ON pu.location_id = t.pu_location_id   -- drops trips whose zone is not in the lookup
JOIN zones dz ON dz.location_id = t.do_location_id
WHERE t.pickup_at >= '2026-07-01' AND t.pickup_at < '2026-10-01'                 -- stray dates from 2008 to 2026-10
  AND t.dropoff_at > t.pickup_at                                                  -- dropoff must come after pickup
  AND EXTRACT(EPOCH FROM (t.dropoff_at - t.pickup_at)) BETWEEN 60 AND 10800       -- 1 minute to 3 hours
  AND t.trip_distance > 0 AND t.trip_distance <= 100                              -- zero-distance and implausible trips
  AND t.trip_distance / (EXTRACT(EPOCH FROM (t.dropoff_at - t.pickup_at)) / 3600.0) <= 80  -- faster than 80 mph is a data error
  AND t.fare_amount > 0 AND t.total_amount > 0;                                   -- refunds, voids and zero fares
