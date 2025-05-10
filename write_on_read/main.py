import os
import json
import shutil
from pyspark.sql import SparkSession
from pyspark.sql.functions import input_file_name, count, col


def update_metadata(df, partition_key, metadata_path):
    df = df.withColumn("filePath", input_file_name())

    # Aggregate total records per file
    total_df = df.groupBy("filePath").agg(count("*").alias("totalRecords"))

    # Aggregate records per partition key + file
    key_df = df.groupBy(partition_key, "filePath").agg(count("*").alias("keyRecordsInFile"))
    joined_df = key_df.join(total_df, on="filePath")

    new_meta = {}

    for row in joined_df.collect():
        key_value = str(row[partition_key])
        new_meta.setdefault(key_value, []).append({
            "relativePath": row["filePath"],
            "KeyrecordsInFile": row["keyRecordsInFile"],
            "totalRecords": row["totalRecords"]
        })

    # Load existing metadata
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
    else:
        metadata = {"keyColumnName": partition_key, "keyValues": {}}

    # Merge metadata
    for k, v in new_meta.items():
        if k in metadata["keyValues"]:
            metadata["keyValues"][k]["files"].extend(v)
        else:
            metadata["keyValues"][k] = {"files": v, "initialized": False}

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def read_and_chunk_on_demand(spark, key, values, metadata_path, output_base_path):
    if not os.path.exists(metadata_path):
        print("No metadata found. Read all raw data.")
        return spark.read.csv(input_path, header=True)

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    key_meta = metadata["keyValues"]

    files_to_read = set()
    keys_to_chunk = []

    for v in values:
        entry = key_meta.get(v)
        if not entry:
            continue
        files = [f["relativePath"] for f in entry["files"]]
        files_to_read.update(files)
        if not entry["initialized"]:
            keys_to_chunk.append(v)

    if not files_to_read:
        print("No files found for provided values.")
        return spark.createDataFrame([], spark.read.csv(input_path, header=True).schema)

    # Load raw files
    raw_df = spark.read.csv(list(files_to_read), header=True)

    # Filter requested keys
    result_df = raw_df.filter(col(key).isin(values))

    # For uninitialized keys, trigger chunking
    for k_val in keys_to_chunk:
        part_df = raw_df.filter(col(key) == k_val)
        output_path = os.path.join(output_base_path, f"{key}={k_val}")
        part_df.write.mode("overwrite").parquet(output_path)

        key_meta[k_val]["initialized"] = True
        key_meta[k_val]["partitionPath"] = output_path
        key_meta[k_val]["files"] = []  # Clean up used entries

    # Save updated metadata
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Return filtered result
    return result_df


# Initialize Spark session
spark = SparkSession.builder.appName("WriteOnReadPartitioning").getOrCreate()

# Configs
partition_key = "country"
input_path = "s3://your-bucket/raw/*.csv"
output_base_path = "s3://your-bucket/partitioned/"
metadata_path = "/mnt/data/wor_metadata.json"  # can be s3 or local path

# Load new raw data
raw_df = spark.read.csv(input_path, header=True)

# 1. Initialize or Update Metadata
update_metadata(raw_df, partition_key, metadata_path)

# 2. Simulate Consumer Query - triggers chunking only if key hasn't been written
result = read_and_chunk_on_demand(spark, partition_key, ["IN", "US", "CN"], metadata_path, output_base_path)
result.show()

