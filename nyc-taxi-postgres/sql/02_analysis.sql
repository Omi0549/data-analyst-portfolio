-- Q1: When is demand highest? Average trips per hour of day, weekday vs weekend (total trips divided by number of days of that type).
WITH daily_hour AS (
    SELECT pickup_date, is_weekend, pickup_hour, count(*) AS trips
    FROM trips_clean
    GROUP BY 1, 2, 3
)
SELECT pickup_hour,
       CASE WHEN is_weekend THEN 'weekend' ELSE 'weekday' END AS day_type,
       round(avg(trips)) AS avg_trips_per_hour
FROM daily_hour
GROUP BY pickup_hour, is_weekend
ORDER BY day_type, pickup_hour;

-- Q2: Which pickup zones generate the most trips? Top 10 with share of all trips and a running share (window functions).
SELECT pu_zone, pu_borough,
       count(*) AS trips,
       round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_of_trips,
       round(100.0 * sum(count(*)) OVER (ORDER BY count(*) DESC) / sum(count(*)) OVER (), 2) AS cumulative_pct
FROM trips_clean
GROUP BY pu_zone, pu_borough
ORDER BY trips DESC
LIMIT 10;

-- Q3: Borough summary by pickup borough: volume, typical fare, distance and duration.
SELECT pu_borough,
       count(*) AS trips,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct_of_trips,
       round(avg(fare_amount)::numeric, 2) AS avg_fare,
       round(avg(trip_distance)::numeric, 2) AS avg_miles,
       round(avg(duration_min)::numeric, 1) AS avg_minutes
FROM trips_clean
GROUP BY pu_borough
ORDER BY trips DESC;

-- Q4: Airport trips versus all other trips: how much more do they pay, and do airport riders tip more? Tips use credit-card trips only.
SELECT CASE WHEN is_airport_trip THEN 'airport' ELSE 'non-airport' END AS trip_type,
       count(*) AS trips,
       round(avg(fare_amount)::numeric, 2) AS avg_fare,
       round(avg(trip_distance)::numeric, 2) AS avg_miles,
       round((avg(fare_amount) / avg(trip_distance))::numeric, 2) AS fare_per_mile,
       round((100 * avg(tip_amount / fare_amount) FILTER (WHERE payment_type = 1))::numeric, 1) AS avg_tip_pct_card
FROM trips_clean
GROUP BY is_airport_trip
ORDER BY trips DESC;

-- Q5: Tip rate by hour of day, credit-card trips only (cash tips are not recorded). Average of per-trip tip % of fare.
SELECT pickup_hour,
       count(*) AS card_trips,
       round((100 * avg(tip_amount / fare_amount))::numeric, 1) AS avg_tip_pct
FROM trips_clean
WHERE payment_type = 1
GROUP BY pickup_hour
ORDER BY pickup_hour;

-- Q6: Daily trips with a trailing 7-day average and change versus the same weekday one week earlier (window functions).
WITH daily AS (
    SELECT pickup_date, count(*) AS trips
    FROM trips_clean
    GROUP BY pickup_date
)
SELECT pickup_date,
       trips,
       round(avg(trips) OVER (ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)) AS trips_7day_avg,
       round(100.0 * (trips - LAG(trips, 7) OVER (ORDER BY pickup_date)) / LAG(trips, 7) OVER (ORDER BY pickup_date), 1) AS pct_vs_week_ago
FROM daily
ORDER BY pickup_date;

-- Q7: Top 3 pickup zones inside each borough using RANK() over a partition.
WITH zone_trips AS (
    SELECT pu_borough, pu_zone, count(*) AS trips
    FROM trips_clean
    GROUP BY pu_borough, pu_zone
), ranked AS (
    SELECT *, RANK() OVER (PARTITION BY pu_borough ORDER BY trips DESC) AS rnk
    FROM zone_trips
)
SELECT pu_borough, rnk, pu_zone, trips
FROM ranked
WHERE rnk <= 3 AND pu_borough NOT IN ('Unknown', 'N/A')
ORDER BY pu_borough, rnk;

-- Q8: Congestion check: average speed and fare per mile by hour for trips starting and ending in Manhattan.
SELECT pickup_hour,
       count(*) AS trips,
       round(avg(avg_mph)::numeric, 1) AS avg_mph,
       round((sum(fare_amount) / sum(trip_distance))::numeric, 2) AS fare_per_mile
FROM trips_clean
WHERE pu_borough = 'Manhattan' AND do_borough = 'Manhattan'
GROUP BY pickup_hour
ORDER BY pickup_hour;

-- Q9: Most common routes (pickup zone to dropoff zone), excluding same-zone trips, with average fare.
SELECT pu_zone, do_zone,
       count(*) AS trips,
       round(avg(fare_amount)::numeric, 2) AS avg_fare
FROM trips_clean
WHERE pu_zone <> do_zone
GROUP BY pu_zone, do_zone
ORDER BY trips DESC
LIMIT 10;
