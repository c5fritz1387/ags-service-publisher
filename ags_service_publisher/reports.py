import csv
import os

from config_io import default_config_dir, get_configs
from datasources import get_mxd_data_sources
from extrafilters import superfilter
from helpers import asterisk_tuple, empty_tuple, file_or_stdout
from logging_io import setup_logger
from services import normalize_services, get_source_info

log = setup_logger(__name__)


def write_report(report_data, header_row=None, report_type='', output_filename=None, output_format='csv'):
    log.info(
        'Generating {} report{}'
        .format(
            report_type,
            ': {}'.format(os.path.abspath(output_filename))
            if output_filename else ''
        )
    )

    if output_format == 'csv':
        with file_or_stdout(output_filename, 'wb') as csv_file:
            csv_writer = csv.writer(csv_file, lineterminator='\n')
            csv_writer.writerow(header_row)
            for row in report_data:
                csv_writer.writerow(row)
    else:
        raise RuntimeError('Unsupported output format: {}'.format(output_format))

    log.info(
        'Successfully generated {} report{}'
        .format(
            ': {}'.format(os.path.abspath(output_filename))
            if output_filename and os.path.isfile(output_filename) else ''
        )
    )
    return output_filename


def find_mxd_data_sources(
    included_configs=asterisk_tuple, excluded_configs=empty_tuple,
    included_users=asterisk_tuple, excluded_users=empty_tuple,
    included_databases=asterisk_tuple, excluded_databases=empty_tuple,
    included_versions=asterisk_tuple, excluded_versions=empty_tuple,
    included_services=asterisk_tuple, excluded_services=empty_tuple,
    included_envs=asterisk_tuple, excluded_envs=empty_tuple,
    included_datasets=asterisk_tuple, excluded_datasets=empty_tuple,
    include_staging_mxds=True,
    warn_on_validation_errors=False,
    config_dir=default_config_dir
):
    for config_name, config in get_configs(included_configs, excluded_configs, config_dir).iteritems():
        env_names = superfilter(config['environments'].keys(), included_envs, excluded_envs)
        services = superfilter(config['services'], included_services, excluded_services)
        default_service_properties = config.get('default_service_properties')

        if not default_service_properties:
            log.debug('No default service properties specified')

        for env_name in env_names:
            log.debug('Finding MXD data sources for config {}, environment {}'.format(config_name, env_name))
            env = config['environments'][env_name]
            staging_dir = env.get('staging_dir')
            source_dir = env['source_dir']
            source_info, errors = get_source_info(services, source_dir, staging_dir, default_service_properties)
            if len(errors) > 0:
                message = 'One or more errors occurred while validating the {} environment for config name {}:\n{}' \
                          .format(env_name, config_name, '\n'.join(errors))
                if warn_on_validation_errors:
                    log.warn(message)
                else:
                    raise RuntimeError(message)
            for service_name, service_type, service_properties in normalize_services(services, default_service_properties):
                if service_type == 'MapServer':
                    def generate_mxd_data_sources_report_rows(mxd_path, mxd_type):
                        for (
                            layer_name,
                            dataset_name,
                            workspace_path,
                            user,
                            database,
                            version,
                            definition_query
                        ) in get_mxd_data_sources(mxd_path):
                            if (
                                superfilter((dataset_name,), included_datasets, excluded_datasets) and
                                superfilter((user,), included_users, excluded_users) and
                                superfilter((database,), included_databases, excluded_databases) and
                                superfilter((version,), included_versions, excluded_versions)
                            ):
                                yield (
                                    config_name,
                                    env_name,
                                    service_name,
                                    mxd_path,
                                    mxd_type,
                                    layer_name,
                                    dataset_name,
                                    user,
                                    database,
                                    version,
                                    workspace_path,
                                    definition_query
                                )

                    if include_staging_mxds:
                        for staging_mxd_path in source_info[service_name]['staging_files']:
                            for row in generate_mxd_data_sources_report_rows(staging_mxd_path, 'staging'):
                                yield row
                    source_mxd_path = source_info[service_name]['source_file']
                    if source_mxd_path:
                        for row in generate_mxd_data_sources_report_rows(source_mxd_path, 'source'):
                            yield row
                    else:
                        log.warn(
                            'No source MXD found for service {}/{} in the {} environment!'
                            .format(config_name, service_name, env_name)
                        )
                else:
                    log.debug(
                        'Unsupported service type {} of service {} will be skipped'
                        .format(service_type, service_name)
                    )
