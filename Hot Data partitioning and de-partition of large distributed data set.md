# Innumerable Hot Data partitioning and de-partition of large distributed data set

## Nirmit Jain jainnirmit8@gmail.com

## Context

In this paper, we primarily refer to large distributed datasets maintained within a data lake, which are either directly queried by end consumers or accessed by multiple consumers with distinct query patterns—some oriented toward analytical workloads, while others are more transactional in nature.

In this paper, we will explore strategies for partitioning data in a way that minimizes downtime, ensures faster performance, and enables a fully autonomous process.

In this paper de partitioning is not detailed but it is the exact opposite process of partition of large datasets. So just to reduce the amount of context it is not being explicitly detailed here. 

## What is a large distributed data set in a data lake?

A **large distributed data set** in a **data lake** refers to a collection of vast and varied data that is, **Massive in size** (potentially terabyte or more) and is **Located within a data lake architecture** (typically built on cloud storage systems like Amazon S3, Azure Data Lake Storage, or Hadoop Distributed File System (HDFS))

Example:

Imagine a company that stores clickstream logs, social media feeds, sensor data, and customer transaction records. This data, distributed across a cloud data lake like AWS S3 and processed with tools like Apache Spark or Presto, forms a **large distributed data set**.

## What is data partitioning?

Data partitioning is a fundamental strategy in data lakehouse architectures, designed to optimize performance, scalability, and manageability.

* Data partitioning is a technique used to divide a large dataset into smaller pieces, called partitions.   
* These partitions are typically stored separately, often on different storage devices or within different tables.   
* Partitioning helps manage large datasets by allowing for parallel processing and improved resource utilization.

## What are the benefits of Data partition?

There is a great blog by Onehouse for understanding this better follow this [link](https://www.onehouse.ai/blog/knowing-your-data-partitioning-vices-on-the-data-lakehouse)

Most query engines leverage **partition pruning** techniques to limit the data search to only those relevant partitions matching conditions specified in the query instead of processing all the partitions. These are achieved via **filters and predicate push-downs** during query analysis and planning phases. Query engines depend on such techniques to devise an optimal plan to execute the query instead of having to scan the entire table data. Partition-pruned executions can be orders of magnitude faster than executing the same query on a non-partitioned table with the same columns and data definitions. 

When queries target partition columns or specific values, predicate pushdown enables the query engine to fetch only the relevant partitions. This significantly reduces query costs by minimizing compute usage, network overhead, and API calls to external systems—ultimately lowering system load and promoting a more efficient, harmonious system.

## What are the disadvantages of Data partitioning?

Data filters and predicate pushdown are highly effective when **partitioning is thoughtfully designed** around actual use cases and query patterns. However, if partitioning is misaligned with how the data is queried, it can become a liability—driving up query costs, increasing data scans, and degrading performance.

For instance, consider an employee directory dataset that includes global employment history, with fields like company type and field of work. If the data is partitioned by field of work but most queries filter by company type, predicate pushdown won’t apply. As a result, the engine must scan unnecessary data, leading to increased compute usage, higher costs, and slower query execution.

Data partitioning can also introduce challenges such as **data skew**, especially when executing complex analytical operations like joins and group-bys. When partitions are unevenly sized, certain operations become bottlenecks, making it difficult to optimize performance. To address this, **additional strategies like salting, hash-based partitioning**, or custom data redistribution often need to be employed—**ironically adding complexity to a system originally partitioned to reduce query cost and improve efficiency**.

## So should we focus on how we choose the right partition column?

The answer isn’t straightforward—real-world applications rarely follow a fixed flow or consistent query patterns. Business needs evolve, data grows in unpredictable ways, and the questions we ask of that data continually change.   
Before we even ask, ***“What should the partitioning column be?”***, we should first ask,   
***“When does partitioning truly become necessary?”***. Understanding the point at which partitioning adds value is critical to making informed and adaptive design choices.

## When does partitioning truly become necessary?

Partitioning is generally not recommended for low-velocity, small-volume datasets—particularly those under 10 GB—unless read patterns justify it.

Key factors to consider:

* Data Volume: If the dataset is only a few gigabytes, most modern query engines or in-memory databases can process it efficiently without the need for partitioning.

* Data Read Pattern: Even with a modest data size, if queries frequently access the dataset may in a magnitude of 100QPD, the effective data scanned can resemble terabyte-scale workloads, making partitioning more valuable.

These challenges typically emerge at scale—when datasets grow significantly or when timely, consistent insights become critical for business operations.

Choosing an effective partitioning scheme for large distributed datasets is only practical when there's a well-defined business problem, with established query patterns and proven methods for extracting insights from the system.

If there's no clear visibility into how the system will evolve over time, how can we reliably predict an optimal partitioning strategy?

## How is partitioning of large datasets typically performed, and under what circumstances does the need for partitioning arise?

The need to partition large datasets typically arises when existing data processing jobs begin to exceed resource limits—either slowing down significantly or incurring higher operational costs. These performance or cost bottlenecks often trigger discussions around introducing partitioning, restructuring the workflow, or even adopting a different technology stack to optimize efficiency and scalability

These discussions often lead to the adoption of a suitable partitioning strategy for the problematic dataset. However, this introduces a new challenge: partitioning existing data to align with the intended query patterns. Organizations then make critical decisions—either to prune or reduce historical data to minimize backfill processing costs, or to retain all historical data, accepting the one-time expense and resource load required to reprocess it at scale.

In many cases, only a subset of the output data experiences high read frequency, while the rest remains largely untouched. Identifying these high-access partitions in advance is challenging, as it requires collecting and analyzing extensive query metadata. Without this insight, it’s difficult to determine which partitions are most accessed and should be optimized.

Additionally, backfilling may be associated with unavailability of data and repartitioning underlying datasets often require rewriting existing queries, which can lead to temporary downtime or disruption in delivering insights.

***“Surely there needs to be a better way of doing these thing”***

Before we dive into optimal partitioning strategies, let's first understand how large distributed query engines and data processing systems operate.

### How large distributed query engines and data processing systems operate?

Large distributed query engines and data processing systems are optimized for parallel data processing across multiple nodes. The majority of processing time is spent on I/O operations—reading and writing large volumes of data from distributed storage systems. Systems like Apache Spark or Presto distribute queries across multiple workers, performing computations in parallel. However, the challenge lies in minimizing I/O bottlenecks, as inefficient data shuffling or excessive disk reads can significantly slow down query execution. Effective partitioning and indexing are crucial to reduce unnecessary data access and improve performance.

When processing large volumes of data for partitioning, the operation can become highly unoptimized. This often involves extensive data shuffling, heavy disk I/O, and repeated read-write cycles. Due to technical constraints—such as limits on memory, I/O bandwidth, or compute quotas—the entire dataset cannot always be loaded or processed in one go. As a result, the system may need to read the input data multiple times, significantly increasing overhead and prolonging the partitioning process

Just-in-time partitioning of data isn’t always necessary—there’s no need to read and rewrite the entire dataset in a single, time-consuming process. Instead, we can perform hot partitioning of data. 

## What is hot data partitioning and how to perform it?

I would like to categorize partitioning strategies into cold data partitioning and hot data partitioning, based on the timing and mechanism of how the data is segmented.

* **Cold Data Partitioning** occurs **on-demand**, typically when a request for data necessitates the creation of a new partition. This method involves **spawning a separate process** dedicated to carrying out the partitioning operation. Since this process is initiated reactively, it may introduce some latency, particularly during high-load periods. Cold partitioning is generally used when the data distribution is not known beforehand or when partitioning is too resource-intensive to be performed proactively.

* **Hot Data Partitioning**, on the other hand, is a more **proactive and lightweight** approach. Instead of physically segmenting the data at the time of the request, the system **generates metadata** that logically links two or more storage locations to the same dataset. This allows the system to **simulate partitioning** without actually moving or duplicating data.

Partitioning in data systems is often touted for its ability to enable filter pruning and predicate pushdown, both of which can improve query performance. The idea is that by knowing exactly where relevant data resides (i.e., the partition path), the system can avoid scanning unnecessary data. However, this approach has a significant limitation: if the system already knows the exact path to the data, the performance gain attributed to partitioning is minimal—you’re essentially just querying data directly, which somewhat defeats the purpose of intelligent data partitioning.

This exposes a flaw in traditional partitioning approaches: they rely heavily on physical data paths, which limits their adaptability and efficiency in dynamic or real-time environments.

To address this, the concept of Hot Partitioning emerges. Rather than depending on static partition paths, Hot Partitioning relies on metadata-driven strategies. It dynamically captures and leverages metadata about how data should be partitioned, allowing the system to simulate partitioning logic on-the-fly without physically restructuring the data. This enables smarter, more robust data access patterns.

Additionally, Hot Partitioning enables the creation of multiple logical partitioning keys for the same dataset, allowing it to support diverse query patterns efficiently. This approach helps mitigate common issues such as data skew, small file proliferation, and inefficient query execution, without the need to physically duplicate or restructure the data.

### How to perform Hot partitioning?

Hot partitioning of data can done in two ways:

* Logical set: We create metadata of the partition strategy and store it as metadata location the underlying files and are not altered in this strategy.  
* Write on Read: Extending Logical set partitioning we enable rewriting of data on read of the data to a new location, this concept is similar to MoR tables in ACID based data lake table strategy.

	

#### Logical set

In this strategy, we collect user-defined inputs—such as the partition keys over which the dataset should be logically segmented. Based on these keys, we generate a structured metadata representation that captures partition-specific information for each key, as illustrated below.
```
\[  
   {  
       "keyColumnName": "partition\_key1",  
       "keyValues": {  
           "v1": \[  
               {  
                   "relativePath": "fileA.csv",  
                   "KeyrecordsInFile": 1000,  
                   "totalRecords": 10000  
               },  
               {  
                   "relativePath": "fileB.csv",  
                   "KeyrecordsInFile": 1000,  
                   "totalRecords": 10000  
               }  
           \],  
           "v2": \[  
               {  
                   "relativePath": "fileC.csv",  
                   "KeyrecordsInFile": 1000,  
                   "totalRecords": 10000  
               },  
               {  
                   "relativePath": "fileB.csv",  
                   "KeyrecordsInFile": 1000,  
                   "totalRecords": 10000  
               }  
           \]  
       }  
   },  
   {  
       "keyColumnName": "partition\_key2",  
       "keyValues": {}  
   }  
\]
```
Each piece of metadata is meaningful and plays a crucial role in identifying the exact paths where specific partition keys reside, thereby **minimizing the amount of data scanned during query execution**.  
The fields "totalRecordsInFile" and "keyRecordsInFile" enable a short-circuiting mechanism, allowing the system to bypass unnecessary records reads. This too reduces I/O operations and accelerates the processing of input data.

Below is the pseudo algorithm to follow for implementing Logical Set:

* Write Algorithm:  
  * Take partition key as input  
  * Enrich data set with record file path and total record per file  
  * For Each partition key perform  
    * Group by over partition key and record file path and store aggregated value of record count per partition key and record file path along with max of total record in file path  
  * Check if the partition metadata exists  
    * If Exists perform merging with existing metadata  
    * If not initialize metadata  
  * The Algorithm does high lights around concurrent write, since that is mostly a widely known algorithm and has ample implementation out in the open source world.  
* Read Algorithm:  
  * Check if the partition metadata exists  
    * If Exists   
      * Push down and list of predicates and get a list of files that needs to be processed.  
      * From the list generated files to process read records from the file where the keys exist.  
    * If not initialize metadata read whole data  
  * The Algorithm does high lights around concurrent read and write, since that is mostly a widely known algorithm and has ample implementation out in the open source world.

##### Drawbacks of Logical Set Hot partitioning:

While logical partitioning can significantly reduce data scans by limiting the number of files read, it does not guarantee a reduction in scanned data volume—especially in cases involving low-cardinality partition keys.

For instance, if partitioning is based on a key with only two distinct values, there's a high likelihood that most of the data will be spread across both partitions. As a result, queries targeting either value may still require reading nearly the entire dataset, leading to increased compute overhead and slower data processing.

##### Advantages of Logical Set Hot Partitioning:

Logical set partitioning is most effective when query patterns are diverse and the partition key has high cardinality.

For example, consider a transaction table where there's a need to partition data based on customer IDs. This approach can lead to significant data skew and the generation of numerous small files, especially if the data distribution is uneven. In such cases, using highly flexible logical set partitioning is a more suitable strategy, as it avoids the pitfalls of physical partitioning while still optimizing query performance and reducing overall data scan.

#### Write on Read

As established, logical set hot partitioning works well for high-cardinality datasets, but proves less effective for low-cardinality scenarios. This raises the question: What approach should be taken when dealing with low-cardinality partition keys?

This is where the concept of "write-on-read" comes into play—a strategy inspired by Merge-on-Read (MoR) table designs. In MoR systems, small files are not immediately compacted during writes. Instead, compaction is deferred to read time, optimizing write performance while merging data only when there is an active consumer. This approach minimizes the impact on overall system throughput by shifting the compute burden to fewer, active read operations.

Extending this concept to low-cardinality datasets, we still begin with the initial logical set partitioning, but we augment it with selective physical partitioning. Instead of performing a full backfill partitioning job, we partition the data incrementally and in chunks, triggered by actual query access patterns. This selective processing allows:

* Efficient resource usage  
* Equilibrated distribution of compute load across consumers  
* And partitioning only for specific key values that are frequently accessed.

The result is a more balanced and responsive system that adapts to real-world usage without overwhelming the storage layer or incurring unnecessary compute overhead.

Below is the pseudo algorithm to follow for implementing Write on read partitioning strategy:

* Write Algorithm Initialisation:  
  * Take partition key as input  
  * Enrich data set with record file path and total record per file  
  * For Each partition key perform  
    * Group by over partition key and record file path and store aggregated value of record count per partition key and record file path along with max of total record in file path  
* Write Algorithm New Input data:  
  * Check if the partition key folder exists  
    * If it does not exists create partition folder and write partition data  
  * For Each partition key value   
    * Update Metadata and enable partition level path initialization if not already  
  * The Algorithm does high lights around concurrent write, since that is mostly a widely known algorithm and has ample implementation out in the open source world.  
* Read Algorithm:  
  * Check if the partition metadata exists  
    * If Exists   
      * Push down and list of predicates and get a list of files that needs to be processed.  
      * If the partition level path is initialised consider whole data partition partition along with list of files from partition metadata  
      * From the list generated files to process read records from the file where the keys exist.  
      * Start a new process to chunk data into partition  
      * Consider a chunk of file from the list of files from partition metadata   
      * Chunking can be done based on number of files or  key value records, per file sort ascendingly and data size and much more  
      * Once chunk of file is done and respective data is written back to partition path  
      * Enable partition path initialization for all the partition key values.  
      * Remove all the list of files that have been chunked from each of the partition key values  
    * If metadata not initialized read whole data  
  * The Algorithm does high lights around concurrent read and write, since that is mostly a widely known algorithm and has ample implementation out in the open source world.

Post Hot partitioning of data using “Write on read” the dataset will look as depicted below 

![][image1]  
In this approach, unprocessed data naturally accumulates all partition key values that have not yet been queried or accessed. This becomes a beneficial byproduct of the Write-on-Read (WoR) Hot Partitioning strategy, where unaccessed data is automatically identified without requiring explicit tracking or additional processing.

##### Advantages of Write on Read

Improved Write Efficiency: Defers physical partitioning, allowing faster, lightweight writes.

* On-Demand Partitioning: Data is physically organized only when accessed, reducing unnecessary computation.  
* Resource Optimization: Focuses compute and storage on frequently queried data.  
* Automatic Cold Data Identification: Unqueried partition keys remain unprocessed, making cold data easy to detect.  
* Supports Concurrency: Designed to handle concurrent reads and writes without conflicts.  
* Flexible and Adaptive: Chunking strategies can be customized based on file size, record count, or access pattern.

##### Disadvantages

* Initial Read Latency: First-time access to unprocessed data may incur extra processing delay.  
* Metadata Overhead: Requires careful tracking of file states, partition keys, and initialization flags.  
* Complex Implementation: Adds logic for chunking, metadata merging, and partition path management.

#### Comparison between Logical Set Hot Partitioning and Write-on-Read (WoR) Hot Partitioning:

| Metric | Logical Set Hot Partitioning | Write-on-Read (WoR) Hot Partitioning |
| :---- | :---- | :---- |
| **Best Use Case** | High-cardinality partition keys, varied query patterns | Low-cardinality partition keys, incremental access patterns |
| **Partitioning Type** | Logical (metadata only) | Hybrid (logical \+ selective physical) |
| **Data Movement** | None — files remain untouched | On-demand, partial data rewriting during reads |
| **Write Performance** | Fast, as no data is rewritten | Fast initially, slows slightly during read-triggered chunking |
| **Read Performance (First Access)** | Fast if metadata is initialized; may scan large files if low cardinality | May incur latency due to chunking and writing during first access |
| **Query Optimization** | Enables filter pruning, short-circuiting on metadata | Enables filter pruning \+ improves layout over time via incremental rewrite |
| **Skew and Small File Mitigation** | Since data is still consolidated small files is avoided | Strong — rewrites help mitigate skew and small file issues |
| **Storage Overhead** | Minimal (no file duplication or movement) | Slightly higher — due to physical partitioning on access |
| **Metadata Management Complexity** | Moderate | High — tracks partition state, file progress, and write status |
| **Cold Data Detection** | Requires explicit tracking | Automatic — non queried data remains unprocessed |
| **Adaptability to Query Patterns** | High — can support multiple logical keys | Very high — adapts to actual access patterns over time |
| **Compute Cost** | Low — avoids physical transformation | Balanced — compute cost deferred and amortized over reads |

## Summary

This paper proposes dynamic partitioning strategies for large distributed datasets in data lakes to optimize performance, reduce downtime, and enable autonomous operation. Traditional cold partitioning is resource-intensive and inflexible, while hot partitioning offers adaptive, metadata-driven methods. Two hot partitioning approaches are detailed:

Logical Set Partitioning – Uses only metadata to simulate partitioning without moving data; best for high-cardinality keys and diverse queries.

Write-on-Read Partitioning – Adds selective physical partitioning triggered by queries; ideal for low-cardinality keys and incremental access patterns.

These approaches improve read efficiency, reduce compute overhead, adapt to evolving query patterns, and simplify cold data identification—making them more scalable and cost-effective for modern data lake architectures.

[image1]: <data:image/png;base64,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>
