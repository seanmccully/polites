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

from datetime import datetime
import mock
import os
import re
import time
from unittest import TestCase

import polites
from polites import cassandra
from polites.exceptions import PolitesException
from polites import utils


class test_config_object(object):
    hostname = 'localhost'
    cass_home = '/tmp'
    cass_error = ''
    cassandra_start_options = ['test', ('test', )]
    cassandra_startup_script = 'test'
    cassandra_user = 'nosey'
    enable_backups = True
    data_file_directories = 'test'
    heap_newgen_size = 'test'
    max_heap_size = 'test'
    commitlog_directory = 'test'
    backup_location = 'test'
    saved_caches_directory = 'test'
    jmx_port = 123
    max_direct_memory = 'test'
    cassandra_stop_script = 'test'
    cassandra_stop_options = ('t', )
    cassandra_process_name = 'cass'
    backup_hour = 1
    cluster_num = 0
    num_nodes = 1
    seed_provider = 'TestObject'
    key_cache_size_in_mb = 1
    key_cache_keys_to_save = True
    row_cache_size_in_mb = 1
    row_cache_keys_to_save = True
    seeds = 'localhost'
    backup_dir = 'test'

    def __dict__(self):
        d = {}
        for k in dir(self):
            d[k] = getattr(self, k)
        return dict(d)


class UtilTests(TestCase):

    def setUp(self):
        self.settings_location = os.path.join(polites.__path__[0], 'settings')

    def test_yaml(self):
        self.assertEqual(None, utils.load_yaml(self.settings_location +
                         '/restore-cassandra.yaml.DNE'))

    def test_update_yaml(self):
        test_data = {'test': False}
        comp_data = {'test': True}
        test_data = utils.update_yaml(test_data, comp_data)
        self.assertEqual(test_data, comp_data)

    def test_get_hostname(self):
        test_str = u'test'
        with mock.patch.object(utils.socket, 'gethostbyname',
                               mock.MagicMock(return_value=test_str)):
            self.assertEqual(utils.get_hostname(), test_str)

    def test_find_www(self):
        with mock.patch.object(utils.os.path, 'exists', mock.MagicMock()):
            self.assertEqual(utils.find_www(),
                             os.path.join('/var', 'www', 'polites'))

    def test_calc_seconds_from_hour(self):
        dt = datetime(year=2013, month=12, day=25, hour=12)
        with mock.patch.object(utils, 'datetime'):
            with mock.patch.object(utils.datetime, 'now',
                                   mock.Mock(return_value=dt)):
                tot_seconds = utils.calc_seconds_from_hour(dt.hour)
                self.assertEqual(tot_seconds, 60 * 60 * 24)

                tot_seconds = utils.calc_seconds_from_hour(dt.hour + 1)
                self.assertEqual(tot_seconds, 60 * 60)

                tot_seconds = utils.calc_seconds_from_hour(dt.hour - 1)
                self.assertEqual(tot_seconds, 60 * 60 * 23)

    def test_handle_pid(self):
        tmp_file = '/tmp/tests'
        utils.handle_pid(tmp_file)
        self.assertTrue(os.path.exists(tmp_file))


class CassandraTests(TestCase):

    def setUp(self):
        self.test_str = 'Test'
        self.settings_location = os.path.join(polites.__path__[0], 'settings')
        self.cass = cassandra.Cassandra(test_config_object,
                                        cassandra.
                                        Cassandra.update_defaults_2_0)

    def test_cassandra_yaml(self):
        self.assertEqual(os.path.join(test_config_object.cass_home,
                                      'conf', 'cassandra.yaml'),
                         self.cass.cassandra_yaml)

    def test_has_been_restored(self):
        self.assertEqual(self.cass.restored, self.cass.has_been_restored())

    def test_backup_enabled(self):
        self.assertEqual(self.cass.backups_enabled(),
                         test_config_object.enable_backups)

    def test_modify_environment(self):
        env = {"HEAP_NEWSIZE": 'test',
               "MAX_HEAP_SIZE": 'test',
               "DATA_DIR": 'test',
               "COMMIT_LOG_DIR": 'test',
               "LOCAL_BACKUP_DIR": 'test',
               "CACHE_DIR": 'test',
               "JMX_PORT": '123',
               "MAX_DIRECT_MEMORY": 'test',
               "cassandra.join_ring": "true"}
        with mock.patch.object(cassandra, 'os', mock.MagicMock()):
            with mock.patch.object(cassandra.os, 'environ'):
                with mock.patch.object(cassandra.os.environ, 'copy',
                                       mock.MagicMock(return_value={})):
                    new_env = self.cass.modify_environment()
                    self.assertEqual(env, new_env)

    def test_run_command(self):

        def raise_os_error(*args, **kwargs):
            raise OSError()

        cassandra.subprocess.Popen = raise_os_error
        self.assertEqual(self.cass._run_command([]), None)

    def test_run_command_returns_true(self):
        mocked = mock.MagicMock()
        mocked.communicate = mock.MagicMock(return_value=[True, True])

        cassandra.subprocess.Popen = mocked
        self.assertTrue(self.cass._run_command([]))

    def test_run_command_raise_exception(self):
        mocked = mock.MagicMock()
        mocked.communicate = mock.MagicMock(return_value=[None, True])
        mocked.returncode = 1
        cassandra.subprocess.Popen = mock.MagicMock(return_value=mocked)
        self.assertRaises(PolitesException,
                          self.cass._run_command, [])

    def test_stop_cassandra(self):
        self.cass._run_command = mock.MagicMock()
        self.assertTrue(self.cass.stop_cassandra())

    def test_monitor_proc(self):
        self.cass._run_command = mock.MagicMock(return_value=True)
        self.assertTrue(self.cass.monitor_proc())

    def test_monitor_proc_false(self):
        self.cass._run_command = mock.MagicMock(return_value=False)
        self.cass.safe_start_cassandra = mock.MagicMock()
        self.assertFalse(self.cass.monitor_proc())
        self.cass.last_safe_start = int(time.time()) 

        def raise_err(*args):
            raise TypeError

        with mock.patch('polites.cassandra.load_config',
                        return_value=test_config_object):
            mocker = mock.patch('polites.cassandra.inspect_cass_log',
                                new=raise_err)
            mocker.start()
            self.cass.start_cassandra()
            self.assertEqual(self.cass.cass_error_msg,
                                 "cassandra doesn't start, no log error")
            mocker.stop()

    def test_node_tool(self):
        command = self.cass._node_tool_command('host', 123, 'test-with')
        self.assertTrue('nodetool' in command)

    def test_take_snapshot(self):
        with mock.patch.object(cassandra, 'schedule_task',
                               mock.MagicMock(return_value=1)):
            self.cass.clear_snapshot = mock.MagicMock(return_value=False)
            self.assertEqual(self.cass.take_snapshot(), 1)

    def test_take_snapshot_false(self):
        self.cass.clear_snapshot = mock.MagicMock(return_value=True)
        self.cass._get_hostname = mock.MagicMock(return_value='localhost')
        self.cass._run_command = mock.MagicMock(return_value=False)
        self.assertFalse(self.cass.take_snapshot())

    def test_take_snapshot_true(self):
        with mock.patch.object(cassandra, 'schedule_task',
                               mock.MagicMock(return_value=1)):
            self.cass.clear_snapshot = mock.MagicMock(return_value=True)
            self.cass._get_hostname = mock.MagicMock(return_value='localhost')
            self.cass._run_command = mock.MagicMock(return_value='test-out')
            self.cass._match_output = mock.MagicMock(return_value=False)
            self.assertEqual(self.cass.take_snapshot(), 1)

    def test_match_output(self):
        test_str = ['sean is super cool']
        test_re = re.compile('^sean')
        matched = self.cass._match_output(test_str, test_re)
        self.assertEqual(matched.group(), 'sean')

    def test_get_hostname(self):
        self.cass.config.hostname = 'sean'
        self.assertEqual(self.cass._get_hostname(), 'sean')
        self.cass.config.hostname = False
        self.assertEqual(self.cass._get_hostname(), 'localhost')

    def test_clear_snapshot(self):
        self.cass._node_tool_command = mock.MagicMock()
        self.cass._run_command = mock.MagicMock(return_value=False)
        self.assertFalse(self.cass.clear_snapshot())

    def test_clear_snapshot_true(self):
        self.cass._node_tool_command = mock.MagicMock()
        self.cass._run_command = mock.MagicMock(return_value='test')
        self.cass._match_output = mock.MagicMock(return_value=True)
        self.assertTrue(self.cass.clear_snapshot())

    def test_cassandra_get_user(self):
        with mock.patch('polites.cassandra.getuser', return_value='test'):
            test_config_object.cassandra_user = None
            cass = cassandra.Cassandra(test_config_object,
                                       cassandra.
                                       Cassandra.update_defaults_2_0)
            self.assertEqual(cass.config.cassandra_user, 'test')

    def test_cassandra_update_funcs(self):
        yaml_data = {'seed_provider': None,
                     'key_cache_size_in_mb': None}
        self.cass.update_defaults_1_2(yaml_data, hostname='localhost')
        self.assertTrue('row_cache_keys_to_save' in yaml_data)

        yaml_data = {'seed_provider': None,
                     'key_cache_size_in_mb': None}
        self.cass.update_defaults_1_1(yaml_data, hostname='localhost')
        self.assertTrue('row_cache_keys_to_save' in yaml_data)

        test_seeds = [{'parameters': [{'seeds': 'Test'}]}]
        yaml_data = {'seed_provider': test_seeds,
                     'key_cache_size_in_mb': None}
        self.cass.config.seeds = '127.0.0.1'
        self.cass.update_defaults_1_2(yaml_data, hostname='localhost')
        self.assertTrue('seed_provider' in yaml_data)
        self.assertTrue(yaml_data['seed_provider'], test_seeds)


    def test_cassandra_write_yaml(self):
        with mock.patch('__builtin__.open'):
            with mock.patch('polites.cassandra.yaml') as mocked:
                self.cass.write_cassandra_yaml({}, {})
                self.assertTrue(mocked.safe_dump.called)

    def test_find_snapshot(self):
        dirs = [ 'test', '123.tar.gz', 'test3']
        with mock.patch('polites.cassandra.os.path.exists', return_value=True):
            with mock.patch('polites.cassandra.os.listdir', return_value=dirs):
                with mock.patch('polites.cassandra.os.path.isfile',
                                return_value=True):
                    self.cass.find_snapshot() 
                    self.assertEqual(self.cass.latest_snapshot, '123')

    def test_do_restore(self):
        dirs = ['test', 'test2']
        mocks = [mock.MagicMock(path='test_backups', isdir=lambda:False),
                 mock.MagicMock(path='test_snapshots')]
        tarfile = mock.MagicMock()
        tarfile.name = 'test.tar.gz'
        tarfile.getmembers = mock.MagicMock(return_value=mocks)
        self.cass.stop_cassandra = lambda: True
        self.cass.do_tune = lambda: True
        self.cass.safe_start_cassandra = lambda: 'test'
        with mock.patch('polites.cassandra.os') as mocked:
            with mock.patch('polites.cassandra.tarfile.open',
                            return_value=tarfile):
                mocked.path.exists = mock.MagicMock(return_value=True)
                mocked.listdir = mock.MagicMock(return_value=dirs)

                self.assertEqual(self.cass.do_restore('testfun'), 'test')
                self.assertTrue(mocked.remove.called)


class PolitesClient(TestCase):
    pass
