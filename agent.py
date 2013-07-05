

import os
import sys
import argparse
from cassandra import Cassandra
from utils import tune
from settings import priam

from twisted.internet.task import LoopingCall
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor

from hector import Hector, SnapShot, Restore
import logging

LOGGER = logging.getLogger(__name__)

looping_calls = None
commands = ["server", "tune" ]
VERSION = 1

def error_callback(error):
    LOGGER.error("[error_callback] [%s]", error)
    sys.stderr.write(str(error))

def setup_tasks(cass):
    monitor = LoopingCall(cass.monitor_proc, priam)
    deferred = monitor.start(3)
    deferred.addErrback(error_callback)
    if priam.auto_snapshot:
        snapshot = LoopingCall(cass.take_snapshot)
        deferred = snapshot.start(3600 * 12)
        deferred.addErrback(error_callback)
        return (monitor, snapshot, )
    else:
        return (monitor, )

def make_server(cass):
    setup_tasks(cass)
    root = Resource()
    root.putChild('', Hector(cass))
    root.putChild('snapshots', SnapShot(cass))
    root.putChild('restore', Restore(cass))
    application = Site(root)

    reactor.listenTCP(8080, application)
    reactor.run()

def setup_logging():
    logger = logging.getLogger()
    if priam.log_dir:
        handler = logging.FileHandler(priam.log_dir)
    else:
        handler = logging.FileHandler('hector.log')
    if priam.log_format:
        formatter = logging.Formatter(priam.log_format)
    else:
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if priam.log_level:
        logger.setLevel(priam.log_level)
    else:
        logger.setLevel(logging.INFO)

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", help="agent command to run " % commands)
    parser.add_argument("--conf", help="configuration to run tune")
    args = parser.parse_args()

    if VERSION == 1:
        cassandra_conf = 'settings/restore-cassandra-1.2.x.yaml'
    else:
        cassandra_conf = 'settings/incr-restore-cassandra.yaml'

    cass = Cassandra(priam)
    cass.cassandra_defaults = cassandra_conf

    if args.conf:
        cass.cassandra_yaml = args.conf
    else:
         cass.cassandra_yaml = os.path.join(priam.cass_home, 'conf', 'cassandra.yaml')

    if args.command in commands:
        if args.command == commands[0]:
            make_server(cass)
        elif args.command == commands[1]:
            tune(cass, cass.cassandra_yaml, cass.cassandra_defaults)
    elif args.conf:
        raise argparse.ArgumentError(None, "conf needs command")
    else:
        raise argparse.ArgumentError(None, "unknown command")


