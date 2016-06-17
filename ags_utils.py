import getpass
from xml.etree import ElementTree

import requests
from requests.compat import urljoin

from config_io import get_config, default_config_dir
from logging_io import setup_logger

log = setup_logger(__name__)

def generate_token(ags_instance=None, username=None, password=None, expiration=15, config_dir=default_config_dir):
    if not ags_instance:
        ags_instance = raw_input('ArcGIS Server instance: ')
    if not username:
        username = raw_input('User name: ')
    if not password:
        password = getpass.getpass()
    log.info('Generating token for ArcGIS Server instance: {}, user: {}'.format(ags_instance, username))
    user_config = get_config('userconfig', config_dir)
    ags_props = user_config['ags_instances'][ags_instance]
    baseurl = ags_props['url']
    url = urljoin(baseurl, '/arcgis/admin/generateToken')
    log.debug(url)
    r = requests.post(url, {'username': username, 'password': password, 'client': 'requestip', 'expiration': str(expiration),
                            'f': 'json'})
    assert r.status_code == 200
    data = r.json()
    if data.get('status') == 'error':
        raise RuntimeError(data.get('messages'))
    log.info('Successfully generated token for ArcGIS Server instance: {}, user: {}, expires: {}'
             .format(ags_instance, username, data['expires']))
    return data['token']

def list_service_folders(ags_instance, config_dir=default_config_dir):
    log.info('Listing service folders on ArcGIS Server instance {}'.format(ags_instance))
    user_config = get_config('userconfig', config_dir)
    ags_props = user_config['ags_instances'][ags_instance]
    baseurl = ags_props['url']
    token = ags_props['token']
    url = urljoin(baseurl, '/arcgis/admin/services')
    log.debug(url)
    r = requests.get(url, {'token': token, 'f': 'json'})
    assert (r.status_code == 200)
    data = r.json()
    if data.get('status') == 'error':
        log.error(data)
        raise RuntimeError(data.get('messages'))
    service_folders = data['folders']
    return service_folders


def list_services(ags_instance, service_folder=None, config_dir=default_config_dir):
    log.info('Listing services on ArcGIS Server instance {}, Folder: {}'.format(ags_instance, service_folder))
    user_config = get_config('userconfig', config_dir)
    ags_props = user_config['ags_instances'][ags_instance]
    baseurl = ags_props['url']
    token = ags_props['token']
    url = urljoin(baseurl, '/'.join((part for part in ('/arcgis/admin/services', service_folder) if part)))
    log.debug(url)
    r = requests.get(url, {'token': token, 'f': 'json'})
    assert (r.status_code == 200)
    data = r.json()
    if data.get('status') == 'error':
        log.error(data)
        raise RuntimeError(data.get('messages'))
    services = data['services']
    return services


def list_service_workspaces(ags_instance, service_name, service_folder=None, service_type='MapServer',
                            config_dir=default_config_dir):
    if service_type == 'GeometryServer':
        log.warn('Unsupported service type {} for service {} in folder {}'
                 .format(service_type, service_name, service_folder))
        return ()
    log.info('Listing workspaces for service {} on ArcGIS Server instance {}, Folder: {}'
             .format(service_name, ags_instance, service_folder))
    user_config = get_config('userconfig', config_dir)
    ags_props = user_config['ags_instances'][ags_instance]
    baseurl = ags_props['url']
    token = ags_props['token']
    url = urljoin(baseurl, '/'.join((part for part in (
        '/arcgis/admin/services', service_folder, '{}.{}'.format(service_name, service_type),
        'iteminfo/manifest/manifest.xml') if part)))
    log.debug(url)
    r = requests.get(url, {'token': token})
    assert (r.status_code == 200)
    data = r.text
    try:
        datasets = parse_datasets_from_service_manifest(data)
    except:
        log(data)
        raise
    return datasets


def delete_service(ags_instance, service_name, service_folder=None, service_type='MapServer',
                   config_dir=default_config_dir):
    log.info('Deleting service {} on ArcGIS Server instance {}, Folder: {}'
             .format(service_name, ags_instance, service_folder))
    user_config = get_config('userconfig', config_dir)
    ags_props = user_config['ags_instances'][ags_instance]
    baseurl = ags_props['url']
    token = ags_props['token']
    url = urljoin(baseurl, '/'.join((part for part in (
        '/arcgis/admin/services', service_folder, '{}.{}'.format(service_name, service_type), 'delete') if part)))
    log.debug(url)
    r = requests.post(url, {'token': token, 'f': 'json'})
    assert (r.status_code == 200)
    data = r.json()
    if data.get('status') == 'error':
        log.error(data)
        raise RuntimeError(data.get('messages'))
    log.info('Service {} successfully deleted from ArcGIS Server instance {}, Folder: {}'
             .format(service_name, ags_instance, service_folder))

def parse_datasets_from_service_manifest(data):
    xpath = './Databases/SVCDatabase/Datasets/SVCDataset/OnPremisePath'
    tree = ElementTree.fromstring(data)
    subelements = tree.findall(xpath)
    for subelement in subelements:
        yield subelement.text