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

import logging
import os
from Queue import LifoQueue
import re
import yaml

from polites.backwards import BackwardsFileReader
from polites.exceptions import PolitesException
from polites.utils import load_yaml


LOGGER = logging.getLogger(__name__)


def get_cass_log_file(config):
    LOGGER.debug("[get_cass_log_file] called")
    log_yaml = os.path.join(config.cass_home, 'conf',
                            'log4j-server.properties')
    log_file = None
    try:
        yaml_data = load_yaml(log_yaml)
        log_file = yaml_data['log4j.appender.R.file']
    except yaml.error.YAMLError:
        fh = open(log_yaml, 'r')
        for line in fh.readlines():
            if re.match('^log4j.appender.R.File=(.*)$', line):
                log_file = line.split('=')
                if len(log_file):
                    log_file = log_file[1]
                break
        fh.close()
    except TypeError as exc:
        LOGGER.exception("[get_cass_log_file] opening cassandra log yaml [%s]",
                         exc)

    LOGGER.debug("[get_cass_log_file] leaving [%s]", log_file)
    if log_file:
        return log_file.replace('\n', '')
    else:
        raise PolitesException("error finding cassandra log file")


def inspect_cass_log(config):
    cass_log_file = get_cass_log_file(config)
    if not cass_log_file or not os.path.exists(cass_log_file):
        return None

    reader = BackwardsFileReader(cass_log_file)
    lifo = LifoQueue()
    last_line = reader.readline()
    lifo.put(last_line)
    while not re.match('^ERROR', last_line):
        last_line = reader.readline()
        if re.match('^\t', last_line):
            lifo.put(last_line)
        if re.match('^ERROR', last_line):
            lifo.put(last_line)
        if not last_line:
            break

    ret_str = ""
    while not lifo.empty():
        ret_str += lifo.get()
    return ret_str
