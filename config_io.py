import logging
import os
from collections import OrderedDict

import yaml  # PyYAML: http://pyyaml.org/

from extrafilters import superfilter
from helpers import asterisk_tuple

log = logging.getLogger(__name__)

default_config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config'))


def get_config(config_name, config_dir=default_config_dir):
    log.debug('Getting config \'{}\' in directory: {}'.format(config_name, config_dir))
    return read_config_from_file(os.path.abspath(os.path.join(config_dir, config_name + '.yml')))


def get_configs(config_names=asterisk_tuple, config_dir=default_config_dir):
    log.debug('Getting configs \'{}\' in directory: {}'.format(config_names, config_dir))
    if len(config_names) == 1 and config_names[0] == '*':
        config_names = (os.path.splitext(os.path.basename(config_file))[0] for config_file in superfilter(
            os.listdir(config_dir), inclusion_patterns=('*.yml',), exclusion_patterns=('userconfig.yml',)))
    return OrderedDict(((config_name, get_config(config_name, config_dir)) for config_name in config_names))


# From http://stackoverflow.com/a/21912744
def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)


# From http://stackoverflow.com/a/21912744
def ordered_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):
    class OrderedDumper(Dumper):
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items())

    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)


def read_config_from_file(file_path):
    with open(file_path) as f:
        config = ordered_load(f)
        return config


def write_config_to_file(config, file_path):
    with open(file_path, 'wb') as f:
        ordered_dump(config, f)
