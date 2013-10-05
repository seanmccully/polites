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


import os
import sys
import logging
import argparse

from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.internet.task import LoopingCall

__dir__ = os.path.dirname(os.path.abspath(__file__))
__parent__ = os.path.dirname(__dir__)

if 'PYTHONPATH' not in os.environ:
    sys.path.append(__parent__)

import hector
from hector._hector import Hector
from hector._hector import Restore
from hector._hector import SnapShot
from hector.cassandra import Cassandra
from hector.client import HectorClient
from hector.exceptions import HectorException
from hector.utils import calc_seconds_from_hour
from hector.utils import error_callback
from hector.utils import find_www
from hector.utils import get_backup_hour
from hector.utils import load_config
from hector.utils import schedule_task
from hector.utils import set_path
from hector.utils import tune

LOGGER = logging.getLogger(__name__)

COMMANDS = ["server", "tune", "restore", "snapshot", "client"]
CLIENT_COMMANDS = HectorClient.commands

def setup_tasks(cass):
    monitor = LoopingCall(cass.monitor_proc, cass.config)
    deferred = monitor.start(3)
    deferred.addErrback(error_callback)

    if cass.config.auto_snapshot:
        schedule_task(calc_seconds_from_hour(get_backup_hour(cass.config)),
                      cass.take_snapshot)
    if cass.config.enable_backups:
        schedule_task(calc_seconds_from_hour(get_backup_hour(cass.config)),
                      cass.take_backup)


def handle_tune(cass):
    tune(cass)

def run():
    reactor.run()

def make_server(cass):
    setup_tasks(cass)
    root = Resource()
    root.putChild('', Hector(cass))
    root.putChild('snapshot', SnapShot(cass))
    root.putChild('restore', Restore(cass))
    www_path = find_www()
    if www_path:
        root.putChild('docs', File(www_path))
    application = Site(root)

    try:
        handle_tune(cass)
    except IOError:
        LOGGER.exception("[make_server] unable to set configuration")
    reactor.callLater(0, cass.find_snapshot)
    reactor.listenTCP(cass.config.default_web_port, application)
    run()

def is_client(args, cassandra, extra):
    if extra not in CLIENT_COMMANDS:
        HectorException("Invalid Client Command")
    HectorClient(cassandra.config, command=extra)
    run()

def setup_logging(config):
    logger = logging.getLogger()
    if config.log_dir:
        handler = logging.FileHandler(config.log_dir)
    else:
        handler = logging.FileHandler('hector.log')
    if config.log_format:
        formatter = logging.Formatter(config.log_format)
    else:
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if config.log_level:
        logger.setLevel(config.log_level)
    else:
        logger.setLevel(logging.INFO)


def parse_args(args, cassandra, parser, extra):
    if len(extra) > 1:
        raise HectorException("Invalid Command Option")
    elif args.command in COMMANDS:
        args.command = args.command.lower()
        if args.command == COMMANDS[0]:
            return make_server(cassandra)
        elif args.command == COMMANDS[1]:
            return handle_tune(cassandra)
        elif args.command == COMMANDS[2]:
            if args.restore_point:
                restore_point = os.path.join(cassandra.config.backup_dir,
                                             args.restore_point + '.tar.gz')
                return cassandra.do_restore(restore_point)
            else:
                raise HectorException("restore commands restore-point")
        elif args.command.lower == COMMANDS[3]:
            return cassandra.take_snapshot()
        elif args.command == COMMANDS[4]: 
            try:
                return is_client(args, cassandra, extra[0])
            except IndexError:
                return is_client(args, cassandra, CLIENT_COMMANDS[0])
    elif args.cass_conf:
        raise HectorException("conf needs command")

    parser.print_usage()


def use_path(conf):
    ins_pths = [os.path.join(sys.exec_prefix, 'etc', 'hector'),
                os.path.join(sys.exec_prefix, 'local', 'etc', 'hector'),
                os.path.join('/etc', 'hector')]
    if conf:
        return set_path(conf)
    elif os.path.exists(os.path.join(hector.__path__[0], '..', 'settings')):
        set_path(os.path.join(hector.__path__[0], '..', 'settings'))
    else:
        for ins_pth in ins_pths:
            if os.path.exists(os.path.join(ins_pth, 'config.py')):
                return set_path(ins_pth)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", help="agent command to run %s" % COMMANDS)
    parser.add_argument("--conf", help="where to load configuration data")
    parser.add_argument("--cass-conf", help="configuration to tune cassandra")
    parser.add_argument("--restore-point", help="The name of the file to " +
                        "be used as a restore point w/o .tar.gz")
    (args, extra, ) = parser.parse_known_args()

    use_path(args.conf)
    config = load_config()
    setup_logging(config)

    if config.VERSION == 2.0:
        update_func = Cassandra.update_defaults_2_0
    elif config.VERSION == 1.2:
        update_func = Cassandra.update_defaults_1_2
    elif config.VERSION == 1.1:
        update_func = Cassandra.update_defaults_1_1

    cassandra = Cassandra(config, update_func)

    if args.conf:
        cassandra.cassandra_yaml = args.conf
    parse_args(args, cassandra, parser, extra)

if __name__ == "__main__":
    main()
