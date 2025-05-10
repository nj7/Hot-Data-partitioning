import os
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import input_file_name, count, col


def write_logical_partition_metadata(df, partition_keys, metadata_path):
    df = df.withColumn("filePath", input_file_name())

    # Aggregate total records per file
    total_records_df = df.groupBy("filePath").agg(count("*").alias("totalRecords"))

    all_metadata = []

    for key in partition_keys:
        # Aggregate records per partition key + file
        key_records_df = df.groupBy(key, "filePath").agg(count("*").alias("keyRecordsInFile"))
        joined_df = key_records_df.join(total_records_df, on="filePath")

        key_metadata = {
            "keyColumnName": key,
            "keyValues": {}
        }

        for row in joined_df.collect():
            key_value = str(row[key])
            record = {
                "relativePath": row["filePath"],
                "KeyrecordsInFile": row["keyRecordsInFile"],
                "totalRecords": row["totalRecords"]
            }
            key_metadata["keyValues"].setdefault(key_value, []).append(record)

        all_metadata.append(key_metadata)

    # Merge with existing metadata if available
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            existing_metadata = json.load(f)
        # Simple merging logic (extend only)
        for new_meta in all_metadata:
            for old_meta in existing_metadata:
                if new_meta["keyColumnName"] == old_meta["keyColumnName"]:
                    for k, v in new_meta["keyValues"].items():
                        old_meta["keyValues"].setdefault(k, []).extend(v)
                    break
            else:
                existing_metadata.append(new_meta)
        final_metadata = existing_metadata
    else:
        final_metadata = all_metadata

    # Save metadata
    with open(metadata_path, "w") as f:
        json.dump(final_metadata, f, indent=2)


def read_logical_partitioned_data(spark, partition_key, key_values, metadata_path):
    if not os.path.exists(metadata_path):
        print("Metadata not found. Reading all data.")
        return spark.read.csv(input_path, header=True)

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    # Extract metadata for the given partition key
    key_metadata = next((m for m in metadata if m["keyColumnName"] == partition_key), None)
    if not key_metadata:
        print("Partition key not in metadata. Reading full dataset.")
        return spark.read.csv(input_path, header=True)

    # Determine which files to read
    files_to_read = set()
    for val in key_values:
        records = key_metadata["keyValues"].get(str(val), [])
        for rec in records:
            files_to_read.add(rec["relativePath"])

    if not files_to_read:
        print("No relevant files found. Returning empty DataFrame.")
        return spark.createDataFrame([], schema=spark.read.csv(input_path, header=True).schema)

    # Read and filter
    df = spark.read.csv(list(files_to_read), header=True)
    return df.filter(col(partition_key).isin(key_values))


# Initialize Spark
spark = SparkSession.builder.appName("LogicalSetHotPartitioning").getOrCreate()

# Configurable Inputs
partition_keys = ["customer_id"]  # List of partition keys
input_path = "s3://your-bucket/datalake/raw/*.csv"
metadata_path = "/mnt/data/logical_metadata.json"  # or s3://bucket/path/meta.json

# Load data
raw_df = spark.read.csv(input_path, header=True)

# Step 1: Write or update metadata
write_logical_partition_metadata(raw_df, partition_keys, metadata_path)

# Step 2: Read using metadata with pruning
filtered_df = read_logical_partitioned_data(spark, "customer_id", ["C001", "C002"], metadata_path)

filtered_df.show()
