"""
(c) 2013 Sean McCully
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
"""

import re
import os
from getpass import getuser
import sys
import yaml
import time
import tarfile
import logging
import subprocess
from datetime import datetime

from twisted.internet import reactor

from hector.cassandra_log import inspect_cass_log
from hector.exceptions import HectorException
from hector.utils import tune
from hector.utils import schedule_task
from hector.utils import get_backup_hour
from hector.utils import calc_seconds_from_hour
from hector.utils import load_config
from hector.utils import handle_pid
from hector.utils import append_jvm_opt

LOGGER = logging.getLogger(__name__)

SU_COMMAND = "/usr/bin/sudo su %s -c"


class Cassandra(object):
    """
        Cassandra object for monitoring, restoring
    """

    def __init__(self, config, update_func):
        self.config = config
        if not self.config.cassandra_user:
            self.config.cassandra_user = getuser()
        self.su_command = SU_COMMAND % self.config.cassandra_user
        self.last_safe_start = None
        self.cass_error_msg = None
        self.latest_snapshot = None
        self.restored = False
        self.cassandra_running = False
        self.update_defaults = \
            self.__getattribute__(update_func.im_func.func_name)
        self.err_re = re.compile(r".* No such file or directory\s*?$")

    @property
    def cassandra_yaml(self):
        return os.path.join(self.config.cass_home, 'conf', 'cassandra.yaml')

    def has_been_restored(self):
        return self.restored

    def update_defaults_1_2(self, yaml_data, hostname=None):
        self.update_defaults_2_0(yaml_data, hostname=hostname)
        yaml_data['initial_token'] = self._token_gen(ring_size=63)

    def update_defaults_2_0(self, yaml_data, hostname=None):
        """
            Update Cassandra Yaml Config defaults with config data
        """

        LOGGER.debug("[update_defaults_1_2] called")

        def pop_key(lst, k):
            lst.pop(lst.index(k))

        key_list = self.config.__dict__.keys()
        yaml_data['listen_address'] = hostname
        yaml_data['rpc_address'] = hostname
        yaml_data['auto_bootstrap'] = self.has_been_restored()
        yaml_data['incremental_backups'] = self.backups_enabled()
        if self.config.cluster_num:
            yaml_data['initial_token'] = self._token_gen()
        if self.config.num_nodes:
            yaml_data['num_tokens'] = self.config.num_nodes

        self.setup_seeds(yaml_data, key_list, pop_key)
        self.setup_key_row_caches(yaml_data, key_list, pop_key)

        self.set_keys(yaml_data, key_list)
        LOGGER.debug("[update_defaults_1_2] leaving")

    def update_defaults_1_1(self, yaml_data, hostname=None):
        """
            Update Cassandra Yaml Config defaults with config data
        """

        def pop_key(lst, k):
            lst.pop(lst.index(k))

        key_list = self.config.__dict__.keys()
        LOGGER.debug("[update_defaults_1_1] called")
        yaml_data['listen_address'] = hostname
        yaml_data['rpc_address'] = hostname
        yaml_data['initial_token'] = self._token_gen()
        yaml_data['num_tokens'] = self.config.num_nodes
        self.setup_key_row_caches(yaml_data, key_list, pop_key)
        self.setup_seeds(yaml_data, key_list, pop_key)
        self.set_keys(yaml_data, key_list)
        LOGGER.debug("[update_defaults_1_1] leaving")

    def set_keys(self, yaml_data, key_list):
        for key in key_list:
            if (key in yaml_data and getattr(self.config, key) is not None):
                yaml_data[key] = getattr(self.config, key)

    def setup_key_row_caches(self, yaml_data, key_list, pops):
        if self.config.key_cache_size_in_mb:
            yaml_data['key_cache_size_in_mb'] = \
                self.config.key_cache_size_in_mb
            pops(key_list, 'key_cache_size_in_mb')
            if self.config.key_cache_keys_to_save:
                yaml_data['key_cache_keys_to_save'] = \
                    self.config.key_cache_keys_to_save
                pops(key_list, 'key_cache_keys_to_save')

        if self.config.row_cache_size_in_mb:
            yaml_data['row_cache_size_in_mb'] = \
                self.config.row_cache_size_in_mb
            pops(key_list, 'key_cache_size_in_mb')
            if self.config.row_cache_keys_to_save:
                yaml_data['row_cache_keys_to_save'] = \
                    self.config.row_cache_keys_to_save
                pops(key_list, 'row_cache_keys_to_save')

    def setup_seeds(self, yaml_data, key_list, pops):
        """
            Set Seeds from configuration
        """
        try:
            if yaml_data['seed_provider']:
                pops(key_list, 'seed_provider')
                if self.config.seed_provider:
                    yaml_data['seed_provider'][0]['class_name'] = \
                        self.config.seed_provider

                if self.config.seeds:
                    seed_provider = yaml_data['seed_provider'][0]
                    seed_provider['parameters'][0]['seeds'] = self.config.seeds
                    pops(key_list, 'seeds')
        except AttributeError:
            LOGGER.exception("[setup_seeds] Not able to set seed provider")

    def _token_gen(self, ring_size=127):
        return int(self.config.cluster_num * (2 ** ring_size)
                   / self.config.num_nodes)

    def write_cassandra_yaml(self, cassandra_yaml, yaml_data):
        """
            Write Cassandra Yaml config
                cassandra_yaml - location of cassandra Yaml
                yaml_data - Yaml data to write to config
        """
        LOGGER.debug("[write_cassandra_yaml] called")
        fh = open(cassandra_yaml, 'w')
        LOGGER.debug("[write_cassandra_yaml] file handle opened [%s]",
                     cassandra_yaml)

        yaml.safe_dump(yaml_data, fh, canonical=False)
        fh.close()
        LOGGER.debug("[write_cassandra_yaml] leaving [%s]", cassandra_yaml)

    def backups_enabled(self):
        """
            Check if backups are enabled from config
        """
        if self.config.enable_backups:
            return True
        else:
            return False

    @property
    def commitlog_directory(self):
        if type(self.config.commitlog_directory) is list:
            return self.config.commitlog_directory[0]
        else:
            return self.config.commitlog_directory

    def modify_environment(self):
        """
            Modify environment with config
            for running cassandra commands
        """
        env = os.environ.copy()
        new_env_vars = {"HEAP_NEWSIZE": self.config.heap_newgen_size,
                        "MAX_HEAP_SIZE": self.config.max_heap_size,
                        "DATA_DIR": self.data_file_directories,
                        "COMMIT_LOG_DIR": self.commitlog_directory,
                        "LOCAL_BACKUP_DIR": self.config.backup_location,
                        "CACHE_DIR": self.config.saved_caches_directory,
                        "JMX_PORT": str(self.config.jmx_port),
                        "MAX_DIRECT_MEMORY": self.config.max_direct_memory,
                        "cassandra.join_ring": "true"
                        }
        env.update(new_env_vars)
        return env

    def _run_command(self, command, use_su=True):
        """
            Run a cassandra command
        """
        jvm_err = ("The stack size specified is too small," +
                   " Specify at least 228k")
        LOGGER.debug("[_run_command] called with command [%s]", command)
        if use_su:
            commands = self.su_command.split(' ')
            commands.append(command)
        else:
            commands = command.split(' ')
        env = self.modify_environment()
        try:
            ps = subprocess.Popen(commands,
                                  env=env,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        except OSError as exc:
            LOGGER.exception("[_run_command] error running command [%s] [%s]",
                             command, exc)
            return None

        time.sleep(0.1)
        ps.wait()
        output = ps.communicate()
        LOGGER.debug("[_run_command] output [%s]", output)
        if len(output[0]) and jvm_err in output[0]:
            append_jvm_opt(self)
        if output[0]:
            return output[0] or output[1]
        else:
            if ps.returncode == 1 and output[1]:
                LOGGER.error("[_run_command] configuration error, trying to" +
                             " run command that does not exist %s", command)
                raise HectorException("configuration error can't run commands")
            else:
                LOGGER.warn("[_run_command] command failed [%s]", output)
                return None

    def start_cassandra(self):
        """
            Start the cassandra process
        """
        LOGGER.debug("[start_cassandra] called last_safe_start [%s]",
                     self.last_safe_start)
        if not self.last_safe_start:
            self.last_safe_start = int(time.time())
        elif (int(time.time()) - self.last_safe_start) < 30:
            self.config = load_config()
            try:
                self.cass_error_msg = inspect_cass_log(self.config)
            except TypeError:
                LOGGER.exception("[start_cassandra] can't " +
                                 "start cassandra check config.py")
                self.cass_error_msg = "cassandra doesn't start, no log error"
            else:
                self.do_tune()
            LOGGER.warn("[start_cassandra] cassandra error message [%s]",
                        self.config.cass_error)

        pid_loc = os.path.join(*self.config.cassandra_start_options[1])
        handle_pid(pid_loc)
        self.last_safe_start = int(time.time())
        command = ' '.join((self.config.cassandra_startup_script,
                            self.config.cassandra_start_options[0],
                            pid_loc, ))
        output = self._run_command(command)
        if output:
            self.cassandra_running = True
            return True

    def do_tune(self):
        tune(self)

    def stop_cassandra(self):
        """
            Stop the cassandra process
        """
        LOGGER.debug("[stop_cassandra] called")
        command = ' '.join((self.config.cassandra_stop_script,
                            os.path.join(*self.config.cassandra_stop_options)))
        self._run_command(command)
        self.cassandra_running = False
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
        command = "/usr/bin/pgrep -f " + self.config.cassandra_process_name
        output = self._run_command(command, use_su=False)
        if output:
            LOGGER.debug("[monitor_proc] cassandra running [%s]", output)
            self.cassandra_running = True
        else:
            if autostart:
                LOGGER.debug("[monitor_proc] cassandra not running " +
                             "and autostart True")
                self.safe_start_cassandra()
            self.cassandra_running = False

        return self.cassandra_running

    def _node_tool_command(self, hostname, jmx_port, command_option):
        """
            Run a cassandra nodetool command
        """
        command = (os.path.join(self.config.cass_home, 'bin', 'nodetool') +
                   ' -h %s -p %d %s' % (hostname, jmx_port, command_option, ))
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
                LOGGER.debug("[match_output] output matched [%s]", line)
                return matched

        LOGGER.debug("[match_output] leaving")
        return

    def take_snapshot(self):
        """
            Perform snapshot operation
        """
        LOGGER.debug("[take_snapshot] called")

        if self.clear_snapshot():
            command = self._node_tool_command(self._get_hostname(),
                                              self.config.jmx_port, 'snapshot')
            output = self._run_command(command)
            if not output:
                return False

            snapshot_name = re.compile(r'Snapshot directory: (\d+)')
            matched = self._match_output(output.split('\n'), snapshot_name)
            if matched:
                self.latest_snapshot = matched.groups()[0]
                LOGGER.debug("[take_snapshot] output matched [%s]",
                             self.latest_snapshot)
                if reactor.running:
                    return reactor.callLater(1, self.verify_snapshot)
                else:
                    self.verify_snapshot()

        return schedule_task(calc_seconds_from_hour(
                             get_backup_hour(self.config)), self.take_backup)

    def _get_hostname(self):
        try:
            hostname = self.config.hostname
            if not hostname:
                return 'localhost'
        except AttributeError:
            return 'localhost'

        return hostname

    def clear_snapshot(self):
        """
            Clear Snapshots
        """
        LOGGER.debug("[clear_snapshot] called")

        command = self._node_tool_command(self._get_hostname(),
                                          self.config.jmx_port,
                                          'clearsnapshot')
        output = self._run_command(command)
        if output:
            command_success = re.compile(r'^Requested( ' +
                                         'clearing)? snapshot for:')
            if self._match_output(output.split('\n'), command_success):
                return True

        LOGGER.debug("[clear_snapshot] leaving")
        return False

    @property
    def data_file_directories(self):
        if type(self.config.data_file_directories) is list:
            return self.config.data_file_directories[0]
        else:
            return self.config.data_file_directories

    def take_backup(self, backup_name=None):
        """
            Collect incremental backups and compress
        """
        LOGGER.debug("[take_backup] called")
        data_dir = self.data_file_directories
        if type(data_dir) is list:
            data_dir = data_dir[0]
        backup_dir = self.config.backup_dir
        if os.path.exists(data_dir):
            if not backup_name:
                backup_name = datetime.strftime(datetime.now(), "%Y-%m-%dT%H")
            tar_file = os.path.join(backup_dir, backup_name + '.tar.gz')
            tar = tarfile.open(tar_file, 'w:gz')
            for root, dirs, files in os.walk(data_dir):
                LOGGER.debug("[take_backup] walking [%s] [%s] [%s]",
                             root, dirs, files)
                if root.split('/')[-1] == 'backups':
                    tar.add(root)
            tar.close()

        return schedule_task(calc_seconds_from_hour(
                             get_backup_hour(self.config)), self.take_backup)

    def verify_snapshot(self, snapshot_name=None):
        """
            Collect and compress a snapshot
                snapshot_name - snapshot to collect
        """
        LOGGER.debug("[verify_snapshot] called")
        if not snapshot_name:
            snapshot_name = self.latest_snapshot
        LOGGER.debug("[verify_snapshot] snapshot_name [%s]", snapshot_name)

        data_dir = self.data_file_directories
        if type(data_dir) is list:
            data_dir = data_dir[0]
        backup_dir = self.config.backup_dir
        if os.path.exists(data_dir):
            tar_file = os.path.join(backup_dir, snapshot_name + '.tar.gz')
            tar = tarfile.open(tar_file, 'w:gz')
            for root, dirs, files in os.walk(data_dir):
                LOGGER.debug("[verify_snapshot] walking [%s] [%s] [%s]",
                             root, dirs, files)
                if (root.split('/')[-2] == 'snapshots'
                   and root.split('/')[-1] == snapshot_name):
                    tar.add(root)
            tar.close()

    def do_restore(self, restore_point):
        """
            Restore Cassandra from a snapshot
                restore_point - location of snapshot
        """
        LOGGER.debug("[do_restore] called with restore_poit [%s]",
                     restore_point)
        commit_dir = self.commitlog_directory
        if self.stop_cassandra():
            if os.path.exists(commit_dir):
                LOGGER.debug("[do_restore] Removing commitlog [%s]",
                             commit_dir)
                for file in os.listdir(commit_dir):
                    os.remove(os.path.join(commit_dir, file))

            snapshot_file = tarfile.open(restore_point, 'r:gz')
            snapshot_name = snapshot_file.name.split('/')[-1]
            snapshot_name = snapshot_name.replace('.tar.gz', '')

            for file in snapshot_file.getmembers():
                if not file.isdir():
                    if 'snapshots' in file.path:
                        LOGGER.debug("[do_restore] replace snapshot name [%s]",
                                     file.path)
                        file.path = file.path.replace('snapshots/' +
                                                      snapshot_name + '/', '')
                    elif 'backups' in file.path:
                        LOGGER.debug("[do_restore] replace backup name [%s]",
                                     file.path)
                        file.path = file.path.replace('backups/', '')
                    if os.path.exists(file.path):
                        LOGGER.debug("[do_restore] removing file [%s]",
                                     file.path)
                        os.remove(file.path)
                else:
                    if 'snapshots' in file.path:
                        LOGGER.debug("[do_restore] replace snapshot dir [%s]",
                                     file.path)
                        file.path = file.path.replace('snapshots/' +
                                                      snapshot_name, '')
                    elif 'backups' in file.path:
                        LOGGER.debug("[do_restore] replace backups dir [%s]",
                                     file.path)
                        file.path = file.path.replace('backups/', '')

            root = os.path.splitdrive(sys.executable)[0]
            if not root:
                root = '/'
            snapshot_file.extractall(root)
            self.restored = True
            self.do_tune()
        return self.safe_start_cassandra()

    def find_snapshot(self):
        """
            If Snapshot directory exists, report latest snapshot id
        """

        snapshot_id_match = re.compile(r'^(\d+)\.tar\.gz$')
        backup_dir = self.config.backup_dir
        if os.path.exists(backup_dir):
            for file in os.listdir(backup_dir):
                if os.path.isfile(os.path.join(backup_dir, file)):
                    file_match = snapshot_id_match.match(file)
                    if file_match:
                        snapshot_id = file_match.groups()[0]
                        if snapshot_id > self.latest_snapshot:
                            self.latest_snapshot = snapshot_id
