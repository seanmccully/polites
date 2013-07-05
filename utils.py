
import os
import yaml
import logging

LOGGER = logging.getLogger(__name__)


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



def tune(cass, yaml_location, settings):
    fh = open(settings)
    yaml_data = yaml.load(fh)
    cass.update_defaults(yaml_data)
    yaml.dump(yaml_data, open(yaml_location, 'w'))
