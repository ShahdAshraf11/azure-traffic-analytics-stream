
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, when, lit,
    hour as spark_hour, dayofweek, date_format, broadcast
)
from pyspark.sql.types import (
    StructType, StructField,
    StringType, DoubleType, BooleanType, IntegerType
)

#  Configuration 
PG_URL = "jdbc:postgresql://postgres:5432/traffic_db"
PG_PROPERTIES = {
    "user": "postgres",
    "password": "postgres",
    "driver": "org.postgresql.Driver"
}

#  Step 1: Create SparkSession 
spark = SparkSession.builder \
    .appName("TrafficWarehouseStreaming") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

print("=" * 65)
print("  Spark Streaming — Kafka → PostgreSQL Warehouse")
print("  Reading from Kafka topic: traffic-data")
print("  Writing to: warehouse.fact_traffic in PostgreSQL")
print("=" * 65)

#  Step 2: Load dimension tables ONCE at startup 
# These are small (25 locations, 168 time keys, 12 weather keys) so we
# load them once and broadcast them to all Spark workers. Every micro-batch
# joins against these in-memory copies — no need to query Postgres each batch.
print("\n Loading dimension tables for key lookups...")

dim_location = spark.read.jdbc(url=PG_URL, table="warehouse.dim_location",
                                properties=PG_PROPERTIES)
dim_time = spark.read.jdbc(url=PG_URL, table="warehouse.dim_time",
                            properties=PG_PROPERTIES)
dim_weather = spark.read.jdbc(url=PG_URL, table="warehouse.dim_weather",
                               properties=PG_PROPERTIES)

# Broadcast = ship a copy to every worker so joins are fast and don't shuffle
dim_location_b = broadcast(dim_location.select("location_key", "location_name"))
dim_time_b = broadcast(dim_time.select("time_key", "hour", "day_of_week"))
dim_weather_b = broadcast(dim_weather.select("weather_key", "condition"))

print(f"   ✓ Loaded {dim_location.count()} locations")
print(f"   ✓ Loaded {dim_time.count()} time keys")
print(f"   ✓ Loaded {dim_weather.count()} weather keys")

#  Step 3: Define the Kafka message schema 
kafka_message_schema = StructType([
    StructField("request_time", StringType(), True),
    StructField("requested_lat", DoubleType(), True),
    StructField("requested_lon", DoubleType(), True),
    StructField("location_name", StringType(), True),
    StructField("frc", StringType(), True),
    StructField("current_speed", DoubleType(), True),
    StructField("free_flow_speed", DoubleType(), True),
    StructField("current_travel_time", IntegerType(), True),
    StructField("free_flow_travel_time", IntegerType(), True),
    StructField("confidence", DoubleType(), True),
    StructField("road_closure", BooleanType(), True),
    StructField("weather_temp", DoubleType(), True),
    StructField("weather_humid", IntegerType(), True),
    StructField("weather_wind", DoubleType(), True),
    StructField("weather_rain", DoubleType(), True),
    StructField("weather_main", StringType(), True),
])

#  Step 4: Read from Kafka 
df_raw = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "traffic-data") \
    .option("startingOffsets", "latest") \
    .option("kafka.group.id", "spark-warehouse-consumer") \
    .load()

#  Step 5: Parse the JSON messages 
df_parsed = df_raw \
    .selectExpr("CAST(value AS STRING) as json_str") \
    .select(from_json(col("json_str"), kafka_message_schema).alias("data")) \
    .select("data.*")

#  Step 6: Add computed columns 
# These produce the columns we'll need to look up dimension keys.
df_enriched = df_parsed \
    .withColumn("event_time", to_timestamp(col("request_time"))) \
    .withColumn(
        "congestion_ratio",
        when(col("free_flow_speed") > 0,
             col("current_speed") / col("free_flow_speed")
        ).otherwise(0.0)
    ) \
    .withColumn("hour", spark_hour(col("event_time"))) \
    .withColumn("day_of_week", dayofweek(col("event_time")) - 1) \
    .withColumnRenamed("weather_main", "condition")
# Note 1: Spark's dayofweek() returns 1-7 (Sun=1..Sat=7) but our dim_time
#         uses 0-6 (Sun=0..Sat=6). Subtracting 1 aligns the two.
# Note 2: Kafka messages have weather_main but dim_weather has 'condition'.
#         We rename the column so the join works on the same name.

#  Step 7: foreachBatch —> write each micro-batch to PostgreSQL 
# Why foreachBatch?
#   Spark's writeStream.format("jdbc") is NOT supported for streaming.
#   foreachBatch lets us turn each micro-batch into a "regular" DataFrame
#   so we can use the normal .write.jdbc(...) API.
def write_batch_to_warehouse(batch_df, batch_id):
    """Called once per micro-batch (every few seconds)."""
    if batch_df.rdd.isEmpty():
        return

    # Look up dimension keys via broadcast joins (fast, in-memory)
    enriched = batch_df \
        .join(dim_location_b, on="location_name", how="left") \
        .join(dim_time_b, on=["hour", "day_of_week"], how="left") \
        .join(dim_weather_b, on="condition", how="left")

    # Select the columns that warehouse.fact_traffic expects.
    # Adjust this list to match your fact_traffic schema exactly.
    fact_rows = enriched.select(
        col("event_time"),
        col("location_key"),
        col("time_key"),
        col("weather_key"),
        col("current_speed"),
        col("free_flow_speed"),
        col("congestion_ratio"),
        col("road_closure"),
        col("confidence"),
        col("weather_temp").alias("temperature"),
        col("weather_rain").alias("rain_mm"),
        col("weather_humid").alias("humidity"),
        col("weather_wind").alias("wind_speed"),
    )

    fact_rows.write \
        .jdbc(
            url=PG_URL,
            table="warehouse.fact_traffic",
            mode="append",
            properties=PG_PROPERTIES,
        )

    print(f"   Batch {batch_id}: wrote {fact_rows.count()} rows to warehouse.fact_traffic")


#  Step 8: Start the streaming query 
query = df_enriched \
    .writeStream \
    .foreachBatch(write_batch_to_warehouse) \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/spark-warehouse-checkpoints") \
    .start()

print("\n Spark streaming started — writing to warehouse.fact_traffic")
print("   Press Ctrl+C to stop")

query.awaitTermination()