
import yaml
import os
import re
import logging
from utils import load_yaml
from backwards import BackwardsReader
from Queue import LifoQueue

LOGGER = logging.getLogger(__name__)


def get_cass_log_file(config):
    LOGGER.debug("[get_cass_log_file] called")
    log_yaml = os.path.join(config.cass_home, 'conf', 'log4j-server.properties')
    log_file = None
    try:
        yaml_data = load_yaml(log_yaml) 
        log_file = yaml_data['log4j.appender.R.file']
    except yaml.error.YAMLError:
        fh = open(log_yaml, 'r')
        for line in fh.readlines():
            if re.match('^log4j.appender.R.File=(.*)$', line):
                key, log_file = line.split('=')
                break;
        fh.close()

    LOGGER.debug("[get_cass_log_file] leaving [%s]" % log_file)
    return log_file.replace('\n', '')

def inspect_cass_log(config):

    cass_log_file = get_cass_log_file(config)
    if not cass_log_file:
        return None

    reader = BackwardsReader(cass_log_file)
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
