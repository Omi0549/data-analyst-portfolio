-- Q1: Row counts removed by each cleaning rule. A row can fail several rules, so the rule counts add up to more than the total removed.
SELECT
    count(*)                                                                              AS raw_rows,
    count(*) FILTER (WHERE pickup_at < '2026-07-01' OR pickup_at >= '2026-10-01')         AS out_of_range_date,
    count(*) FILTER (WHERE dropoff_at <= pickup_at)                                       AS dropoff_not_after_pickup,
    count(*) FILTER (WHERE dropoff_at > pickup_at
        AND EXTRACT(EPOCH FROM (dropoff_at - pickup_at)) NOT BETWEEN 60 AND 10800)        AS duration_out_of_range,
    count(*) FILTER (WHERE trip_distance <= 0)                                            AS zero_distance,
    count(*) FILTER (WHERE trip_distance > 100)                                           AS over_100_miles,
    count(*) FILTER (WHERE fare_amount <= 0)                                              AS nonpositive_fare,
    count(*) FILTER (WHERE total_amount <= 0)                                             AS nonpositive_total,
    (SELECT count(*) FROM trips_clean)                                                    AS clean_rows,
    round(100.0 * (SELECT count(*) FROM trips_clean) / count(*), 2)                       AS pct_kept
FROM trips_raw;

-- Q2: Payment types. Tips are only recorded for credit cards, so tip analysis must filter to payment_type 1.
SELECT payment_type,
       count(*)                                          AS trips,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct_of_trips,
       round(avg(tip_amount)::numeric, 2)                AS avg_tip,
       count(*) FILTER (WHERE passenger_count IS NULL)   AS null_passenger_count
FROM trips_clean
GROUP BY payment_type
ORDER BY trips DESC;

-- Q3: Trips per month in the clean data, to confirm all three months are present.
SELECT date_trunc('month', pickup_date)::date AS month,
       count(*)                                AS trips,
       round(sum(fare_amount)::numeric, 0)     AS fare_total
FROM trips_clean
GROUP BY 1
ORDER BY 1;
