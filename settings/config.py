"""
(c) 2013 Sean McCully
Licenced under the Apache License, 2.0: http://opensource.org/licenses/apache2.0.php
"""
#Hector config properties
##Cassandra Process Name - used to check if process running
cassandra_process_name = "CassandraDaemon"
cassandra_user = None
##Cassandra start/stop commands
cassandra_pid = ('/', 'var', 'lib', 'cassandra', 'cassandra.pid', )
cassandra_start_options = ('-p', cassandra_pid, )
cassandra_stop_options = cassandra_pid
cassandra_startup_script = "/var/lib/cassandra/bin/cassandra"
cassandra_stop_script = "/var/lib/cassandra/bin/stop-server"
VERSIONS = (1.1, 1.2, 2.0, )
VERSION = VERSIONS[-1]
##Cassandra Yaml File based on Version
config_11_yaml = 'restore-cassandra-1.1.yaml'
config_12_yaml = 'restore-cassandra-1.2.yaml'
config_20_yaml = 'restore-cassandra.yaml'

##Location Snapshots and Backups are saved
backup_dir = "/mnt/backup"
log_dir = None
log_format = None
log_level = 30
cass_error = ""
auto_snapshot = True
enable_backups = True
backup_hour = 3
##Number of Cluster Nodes for Token Generation
cluster_num = 0
##Cassandra HOME
cass_home = "/var/lib/cassandra"
default_web_port = 8080
hostname = 'localhost'

#Cassandra YAML properties
authenticator = "AllowAllAuthenticator"
##authorizer = "org.apache.cassandra.auth.AllowAllAuthority"
authorizer = "AllowAllAuthorizer"
authority = "org.apache.cassandra.auth.AllowAllAuthority"
cluster_name = "Test Cluster"
commitlog_directory = ["/var/lib/cassandra/commitlog"]
compaction_throughput_mb_per_sec = 8
data_file_directories = ["/var/lib/cassandra/data"]
endpoint_snitch = "SimpleSnitch"
##endpoint_snitch = "org.apache.cassandra.locator.Ec2Snitch"
hinted_handoff_throttle_in_kb = 1024
in_memory_compaction_limit_in_mb = 128
stream_throughput_outbound_megabits_per_sec = 400
incremental_backups = True
memtable_total_space_in_mb = 1024
jmx_port = 7199
storage_port = 7000
saved_caches_directory = "/var/lib/cassandra/saved_caches"
max_hint_window_in_ms = 8
partitioner = "org.apache.cassandra.dht.RandomPartitioner"
rpc_port = 9160
seed_provider = None
seeds = '127.0.0.1'
ssl_storage_port = 7001
num_nodes = 2


#Cassandra Environment SEttings
heap_newgen_size = "1G"
max_heap_size = "2G"
backup_location = "backup"
max_direct_memory = "5G"

#Unused Config Options
permissions_validity_in_ms = None
column_index_size_in_kb = None
commitlog_segment_size_in_mb = None
commitlog_sync = None
commitlog_sync_period_in_ms = None
compaction_preheat_key_cache = None
concurrent_reads = None
concurrent_writes = None
cross_node_timeout = None
disk_failure_policy = None
dynamic_snitch_badness_threshold = None
dynamic_snitch_reset_interval_in_ms = None
dynamic_snitch_update_interval_in_ms = None
flush_largest_memtables_at = None
hinted_handoff_enabled = None
index_interval = None
internode_compression = None
key_cache_save_period = None
key_cache_size_in_mb = None
memtable_flush_queue_size = None
multithreaded_compaction = False
range_rpc_timeout_in_ms = None
read_rpc_timeout_in_ms = None
reduce_cache_capacity_to = None
reduce_cache_sizes_at = None
request_scheduler = None
row_cache_provider = None
row_cache_save_period = None
row_cache_size_in_mb = None
row_cache_keys_to_save = None
rpc_address = None
rpc_keepalive = None
rpc_server_type = None
rpc_timeout_in_ms = None
server_encryption_options = None
snapshot_before_compaction = None
start_native_transport = None
start_rpc = None
thrift_framed_transport_size_in_mb = None
thrift_max_message_length_in_mb = None
trickle_fsync = None
trickle_fsync_interval_in_kb = None
truncate_rpc_timeout_in_ms = None
write_rpc_timeout_in_ms = None
restore_snapshot = None
client_encryption_options = None
