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
import hector
import imp
import logging
import socket
import yaml

from datetime import datetime
from hector.exceptions import HectorException
from twisted.internet import reactor

LOGGER = logging.getLogger(__name__)

USE_PATH = None


def load_yaml(cassandra_yaml):
    LOGGER.debug("[load_yaml] called [%s]" % cassandra_yaml)
    if os.path.exists(cassandra_yaml):
        fh = open(cassandra_yaml)
        data_map = yaml.safe_load(fh)
        fh.close()
        return data_map


def update_yaml(yaml_data, config):
    for key in config:
        if key in yaml_data:
            yaml_data[key] = config[key]
    return yaml_data


def get_hostname():
    try:
        return socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        return '127.0.0.1'


def find_www():
    def_ins_www = os.path.join('/var', 'www', 'hector')
    alt_www = os.path.join(hector.__path__[0], '..', 'docs')
    if os.path.exists(def_ins_www):
        return def_ins_www
    elif os.path.exists(alt_www):
        return alt_www


def set_path(pth):
    global USE_PATH
    USE_PATH = pth
    return USE_PATH


def load_config():
    try:
        return imp.load_source('config', os.path.join(USE_PATH, 'config.py'))
    except (TypeError, IOError):
        raise HectorException("Config Does Not Exists [%s]" % USE_PATH)


def conf_file(cass):
    try:
        if cass.config.VERSION == 2.0:
            return os.path.join(USE_PATH, cass.config.config_20_yaml)
        elif cass.config.VERSION == 1.2:
            return os.path.join(USE_PATH, cass.config.config_12_yaml)
        elif cass.config.VERSION == 1.1:
            return os.path.join(USE_PATH, cass.config.config_11_yaml)
    except AttributeError:
        raise HectorException("Invalid Path [%s]" % USE_PATH)


def tune(cass):
    fh = open(conf_file(cass))
    yaml_data = yaml.load(fh)
    if cass.config.hostname:
        hostname = cass.config.hostname
    else:
        hostname = get_hostname()

    cass.update_defaults(yaml_data, hostname=hostname)
    yaml.dump(yaml_data, open(cass.cassandra_yaml, 'w'))


def calc_seconds_from_hour(hour):
    seconds_in_hour = 60 * 60
    current_time = datetime.now()
    cur_hour = current_time.hour
    tot_seconds = 0
    if cur_hour > hour:
        tot_seconds = (24 - cur_hour) * seconds_in_hour
        tot_seconds += hour * seconds_in_hour
    elif cur_hour == hour:
        tot_seconds = 24 * seconds_in_hour
    else:
        tot_seconds = (hour - cur_hour) * seconds_in_hour

    tot_seconds -= current_time.minute * 60
    tot_seconds -= current_time.second
    return tot_seconds


def handle_pid(file_location):
    try:
        os.stat(file_location)
    except OSError:
        f = open(file_location, 'a')
        f.close()


def get_backup_hour(config):
    if not config.backup_hour:
        backup_hour = 1
    else:
        backup_hour = config.backup_hour
    return backup_hour


def schedule_task(hour, func):
    if reactor.running:
        return reactor.callLater(calc_seconds_from_hour(hour), func)


def error_callback(error):
    LOGGER.error("[error_callback] Error Logged [%s]" % error)
