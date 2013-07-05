
#from boto.s3.multipart import MultiPartUpload
from twisted.internet import reactor
from xml.etree.ElementTree as ET
import yaml
import time
import re
import os
import sys
import subprocess
import tarfile
from datetime import datetime
import logging
from cassandra_log import inspect_cass_log
from utils import tune

LOGGER = logging.getLogger(__name__)

SUDO_COMMAND = "/usr/bin/sudo -n -E "




class Cassandra(object):
    """
        Cassandra object for monitoring, restoring
    """

    def __init__(self, config):
        self.config = config
        self.last_safe_start = None
        self.cassandra_yaml = None
        self.cassandra_defaults = None
        self.cass_error_msg = None
        self.latest_snapshot = None
        self.restored = False


    def has_been_restored(self):
        return self.restored


    def update_defaults(self, yaml_data, hostname=None):
        """
            Update Cassandra Yaml Config defaults with config data
        """

        LOGGER.debug("[update_defaults] called")
        yaml_data['cluster_name'] = self.config.cluster_name
        yaml_data['storage_port'] = self.config.storage_port
        yaml_data['ssl_storage_port'] = self.config.ssl_storage_port
        yaml_data['rpc_port'] = self.config.rpc_port
        yaml_data['listen_address'] = hostname
        yaml_data['rpc_address'] = hostname
        yaml_data['auto_bootstrap'] = self.has_been_restored()
        yaml_data['saved_caches_directory'] = self.config.saved_caches_directory
        yaml_data['commitlog_directory'] = self.config.commitlog_directory
        yaml_data['data_file_directories'] = [self.config.data_file_directories]
        yaml_data['incremental_backups'] = self.backups_enabled() 
        yaml_data['endpoint_snitch'] = self.config.endpoint_snitch
        yaml_data['in_memory_compaction_limit_in_mb'] = self.config.in_memory_compaction_limit_in_mb
        yaml_data['compaction_throughput_mb_per_sec'] = self.config.compaction_throughput_mb_per_sec
        yaml_data['partitioner'] = self.config.partitioner
        yaml_data['memtable_total_space_in_mb'] = self.config.memtable_total_space_in_mb
        yaml_data['stream_throughput_outbound_megabits_per_sec'] = self.config.stream_throughput_outbound_megabits_per_sec
        yaml_data['multithreaded_compaction'] = self.config.multithreaded_compaction
        yaml_data['max_hint_window_in_ms'] = self.config.max_hint_window_in_ms
        yaml_data['hinted_handoff_throttle_in_kb'] = self.config.hinted_handoff_throttle_in_kb
        yaml_data['authenticator'] = self.config.authenticator
        yaml_data['authorizer'] = self.config.authorizer
        yaml_data['initial_token'] = self._token_gen()
        yaml_data['num_tokens'] = self.config.num_nodes
        try:
            if yaml_data['seed_provider']:
                if self.config.seed_provider:
                    yaml_data['seed_provider'][0]['class_name'] = self.config.seed_provider 
                if self.config.seeds:
                    yaml_data['seed_provider'][0]['parameters'][0]['seeds'] = self.config.seeds
        except AttributeError:
            pass

        if self.config.key_cache_size_in_mb:
            yaml_data['key_cache_size_in_mb'] = self.config.key_cache_size_in_mb
            if self.config.key_cache_keys_to_save:
                yaml_data['key_cache_keys_to_save'] = self.config.key_cache_keys_to_save

        if self.config.row_cache_size_in_mb:
            yaml_data['row_cache_size_in_mb'] = self.config.row_cache_size_in_mb
            if self.config.row_cache_keys_to_save:
                yaml_data['row_cache_keys_to_save'] = self.config.row_cache_keys_to_save
        LOGGER.debug("[update_defaults] leaving")

    def _token_gen(self):
        return int(self.config.cluster_num*(2**127)/self.config.num_nodes)

    def write_cassandra_yaml(cassandra_yaml, yaml_data):
        """
            Write Cassandra Yaml config
                cassandra_yaml - location of cassandra Yaml
                yaml_data - Yaml data to write to config
        """
        LOGGER.debug("[write_cassandra_yaml] called")
        fh = open(cassandra_yaml, 'w')
        LOGGER.debug("[write_cassandra_yaml] file handle opened [%s]", cassandra_yaml)
        yaml.safe_dump(yaml_data, fh, canonical=False)
        fh.close()
        LOGGER.debug("[write_cassandra_yaml] leaving [%s]", cassandra_yaml)

    def backups_enabled(self):
        """
            Check if backups are enabled from config
        """
        if self.config.racs and self.config.backup_racs:
            return ((self.config.incremental_backups and self.config.backup_hour > 0) and
                self.config.backup_racs in self.config.racs)
        else:
            return False

    def modify_environment(self):
        """
            Modify environment with config 
            for running cassandra commands
        """
        env = os.environ.copy()
        new_env_vars = {"HEAP_NEWSIZE": self.config.heap_newgen_size,
                        "MAX_HEAP_SIZE": self.config.max_heap_size,
                        "DATA_DIR": self.config.data_directory,
                        "COMMIT_LOG_DIR": self.config.commitlog_directory,
                        "LOCAL_BACKUP_DIR": self.config.backup_location,
                        "CACHE_DIR": self.config.saved_caches_directory,
                        "JMX_PORT": str(self.config.jmx_port),
                        "MAX_DIRECT_MEMORY": self.config.max_direct_memory,
                        "cassandra.join_ring": "true"
                        }
        env.update(new_env_vars)
        return env

    def _run_command(self, command):
        """
            Run a cassandra command
        """
        LOGGER.debug("[run_command] called with command [%s]", command)
        command = command.split(' ')
        env = self.modify_environment()
        try:
            ps = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            return None

        if ps.stdout:
            output = ps.stdout.read()
            LOGGER.debug("[run_command] output [%s]", output)
            ps.stdout.close()
            ps.wait()
            return output
        else:
            LOGGER.debug("[run_command] stdout empty")
            return None

    def start_cassandra(self):
        """
            Start the cassandra process
        """
        LOGGER.debug("[start_cassandra] called last_safe_start [%s]" % self.last_safe_start)
        if not self.last_safe_start:
            self.last_safe_start = int(time.time())
        elif (int(time.time()) - self.last_safe_start) < 30:
            self.config = reload(self.config)
            self.cass_error_msg = inspect_cass_log(self.config)
            self.do_tune()
            LOGGER.warn("[start_cassandra] cassandra error message [%s]" % self.config.cass_error)

        self.last_safe_start = int(time.time())
        command = SUDO_COMMAND + self.config.cassandra_startup_script 
        output = self._run_command(command)
        if output:
            return True

    def do_tune(self):
        tune(self, self.cassandra_yaml, self.cassandra_defaults)

    def stop_cassandra(self):
        """
            Stop the cassandra process
        """
        LOGGER.debug("[stop_cassandra] called")
        command = SUDO_COMMAND + self.config.cassandra_stop_script
        output = self._run_command(command)
        if output:
            return True

    def safe_start_cassandra(self):
        """
            Make sure cassandra process has been stopped before starting
        """
        LOGGER.debug("[safe_start_cassandra] called")
        self.stop_cassandra()
        if self.start_cassandra():
            return True

    def monitor_proc(self, autostart=True):
        """
            Check if Cassandra process is running
                autostart - If true start process if not running
        """
        LOGGER.debug("[monitor_proc] called")
        command =  "pgrep -f " + self.config.cassandra_process_name
        output = self._run_command(command)
        if output:
            LOGGER.debug("[monitor_proc] cassandra running [%s]" % output)
            self.cassandra_running = True
        else:
            if autostart:
                LOGGER.debug("[monitor_proc] cassandra not running and autostart True")
                self.safe_start_cassandra()
            self.cassandra_running = False

        return self.cassandra_running 

    def _node_tool_command(self, hostname, jmx_port, command_option):
        """
            Run a cassandra nodetool command
        """
        command = os.path.join(self.config.cass_home, 'bin', 'nodetool') + ' -h %s -p %d %s' % (hostname, jmx_port, command_option, ) 
        return command

    def _match_output(self, output, match):
        """
            Match command out with a compiled regex
                match - compiled regex expression
                output - to match against
        """
        LOGGER.debug("[match_output] called")
        for line in output:
            matched = match.match(line)
            if line and matched: 
                LOGGER.debug("[match_output] output matched [%s]" % line)
                return matched

        LOGGER.debug("[match_output] leaving")
        return False

    def take_snapshot(self):
        """
            Perform snapshot operation
        """
        LOGGER.debug("[take_snapshot] called")
        snapshot_name = datetime.strftime(datetime.now(), "%Y%m%d")
        LOGGER.debug("[snapshot_name] snapshot_name [%s]" % snapshot_name)

        try:
            hostname = self.config.hostname
        except AttributeError:
            hostname = 'localhost'

        if self.clear_snapshot():
            command = self._node_tool_command(hostname, self.config.jmx_port, 'snapshot')
            output = self._run_command(command)
            snapshot_name = re.compile('Snapshot directory: (\d+)')

            matched = self._match_output(output.split('\n'), snapshot_name)
            if matched:
                self.latest_snapshot = matched.groups()[0]
                return reactor.callLater(1, self.verify_snapshot)

        return False


    def clear_snapshot(self):
        """
            Clear Snapshots
        """
        LOGGER.debug("[clear_snapshot] called")
        try:
            hostname = self.config.hostname
        except AttributeError:
            hostname = 'localhost'

        command = self._node_tool_command(hostname, self.config.jmx_port, 'clearsnapshot')
        output = self._run_command(command)
        command_success = re.compile('^Requested snapshot for:')

        if self._match_output(output.split('\n'), command_success):
            return True

        LOGGER.debug("[clear_snapshot] leaving")
        return False

    def take_backup(self, data_dir, backup_dir, backup_name=None):
        """
            Collect incremental backups and compress
        """
        LOGGER.debug("[take_backup] called")
        if os.path.exists(data_dir):
            if not backup_name:
                backup_name = datetime.strftime(datetime.now(), "%Y-%m-%dT%H")
            tar_file = os.path.join(backup_dir, backup_name + '.tar.gz')
            tar = tarfile.open(tar_file, 'w:gz')
            for root, dirs, files in os.walk(data_dir):
                if root.split('/')[-1] == 'backups':
                    tar.add(root)
            tar.close()

    def verify_snapshot(self, snapshot_name=None):
        """
            Collect and compress a snapshot
                snapshot_name - snapshot to collect
        """
        LOGGER.debug("[verify_snapshot] called")
        if not snapshot_name:
            snapshot_name = self.latest_snapshot
        LOGGER.debug("[verify_snapshot] snapshot_name [%s]" % snapshot_name)

        data_dir = self.config.data_file_directories 
        backup_dir = self.config.backup_dir
        if os.path.exists(data_dir):
            tar_file = os.path.join(backup_dir, snapshot_name + '.tar.gz')
            tar = tarfile.open(tar_file, 'w:gz')
            for root, dirs, files in os.walk(data_dir):
                if root.split('/')[-2] == 'snapshots' and root.split('/')[-1] == snapshot_name:
                    tar.add(root)
            tar.close()

    def do_restore(self, restore_point):
        """
            Restore Cassandra from a snapshot
                restore_point - location of snapshot
        """
        if self.stop_cassandra():
            if os.path.exists(self.config.commitlog_directory):
                for file in os.listdir(self.config.commitlog_directory):
                    os.remove(os.path.join(self.config.commitlog_directory, file))

            snapshot_file = tarfile.open(restore_point, 'r:gz')
            snapshot_name = snapshot_file.name.split('/')[-1]
            snapshot_name = snapshot_name.replace('.tar.gz', '')

            for file in snapshot_file.getmembers():
                if not file.isdir():
                    file.path = file.path.replace('snapshots/' + snapshot_name + '/', '')
                    if os.path.exists(file.path):
                        os.remove(file.path)
                else:
                    file.path = file.path.replace('snapshots/' + snapshot_name, '')
            root = os.path.splitdrive(sys.executable)[0]
            snapshot_file.extractall(root)
            self.restored = True
            self.do_tune()
        return self.start_cassandra()

