from __future__ import unicode_literals

import os
import re
import fnmatch

from helpers import list_files_in_dir, deep_get
from logging_io import setup_logger

log = setup_logger(__name__)


def list_mxds_in_folder(mxd_dir):
    log.debug('Listing MXDs in folder: {}'.format(mxd_dir))
    return list_files_in_dir(mxd_dir, ext='.mxd')


def list_sde_connection_files_in_folder(sde_connections_dir):
    log.debug('Listing SDE connection files in folder: {}'.format(sde_connections_dir))
    return list_files_in_dir(sde_connections_dir, ext='.sde')


def get_unique_data_sources(mxd_paths, include_table_views=True):
    log.debug('Getting unique data sources for MXD paths: {}'.format(mxd_paths))
    data_sources = []
    for mxd_path in mxd_paths:
        data_sources.extend([data_source[2] for data_source in get_mxd_data_sources(mxd_path, include_table_views)])
    unique_data_sources = list(set(data_sources))
    return unique_data_sources


def open_mxd(mxd_path):
    if not os.path.isfile(mxd_path):
        raise RuntimeError('MXD {} does not exist!'.format(mxd_path))

    import arcpy
    return arcpy.mapping.MapDocument(mxd_path)


def list_layers_in_mxd(mxd, include_table_views=True):
    log.debug('Listing layers in MXD: {}'.format(mxd.filePath))

    import arcpy
    layers = arcpy.mapping.ListLayers(mxd)
    if include_table_views:
        layers.extend(arcpy.mapping.ListTableViews(mxd))
    for layer in layers:
        yield layer


def get_mxd_data_sources(mxd_path, include_table_views=True):
    log.debug('Getting data sources for MXD: {}'.format(mxd_path))

    for layer in list_layers_in_mxd(open_mxd(mxd_path), include_table_views):
        if hasattr(layer, 'workspacePath'):
            yield get_layer_properties(layer)


def get_layer_properties(layer):
    layer_name = layer.longName if hasattr(layer, 'longName') else layer.name
    log.debug('Getting properties for layer: {}'.format(layer_name))

    if hasattr(layer, 'workspacePath'):
        (
            definition_query,
            show_labels,
            symbology_type,
            symbology_field,
            user,
            version,
            service
        ) = (
            deep_get(layer, attr, 'n/a') for attr in (
                'definitionQuery',
                'showLabels',
                'symbologyType',
                'symbology.valueField',
                'serviceProperties.UserName',
                'serviceProperties.Version',
                'serviceProperties.Service'
            )
        )
        database = parse_database_from_service_string(service)

        result = dict(
            layer_name=layer_name,
            dataset_name=layer.datasetName,
            workspace_path=layer.workspacePath,
            is_broken=layer.isBroken,
            user=user,
            database=database,
            version=version,
            definition_query=definition_query,
            show_labels=show_labels,
            symbology_type=symbology_type,
            symbology_field=symbology_field
        )

        log.debug(
            'Layer name: {layer_name}, '
            'Dataset name: {dataset_name}, '
            'Workspace path: {workspace_path}, '
            'Data source is broken: {is_broken}, '
            'User: {user}, '
            'Database: {database}, '
            'Version: {version}, '
            'Definition query: {definition_query}, '
            'Show labels: {show_labels}, '
            'Symbology type: {symbology_type}, '
            'Symbology field: {symbology_field}'
            .format(**result)
        )

        return result
    else:
        raise RuntimeError('Unsupported layer: {}'.format(layer_name))


def get_layer_fields(layer):
    log.debug('Getting fields for layer: {}'.format(layer.longName if hasattr(layer, 'longName') else layer.name))
    import arcpy
    desc = arcpy.Describe(layer)
    fields = desc.fields
    indexes = desc.indexes
    for field in fields:
        in_definition_query = field.name.lower() in layer.definitionQuery if hasattr(layer, 'definitionQuery') else False
        yield dict(
            field_name=field.name,
            field_type=field.type,
            has_index=get_field_index(field, indexes),
            in_definition_query=in_definition_query,
            **find_field_in_label_classes(layer, field)
        )


def get_field_index(field, indexes):
    field_name = field.name
    log.debug('Getting index for field: {}'.format(field_name))
    has_index = False
    for index in indexes:
        for index_field in index.fields:
            if has_index:
                break
            if index_field.name == field_name:
                has_index = True
                break
        if has_index:
            break
    return has_index


def find_field_in_label_classes(layer, field):
    in_label_class_expression = in_label_class_sql_query = False
    if (hasattr(layer, 'showLabels') and layer.showLabels) and hasattr(layer, 'labelClasses'):
        label_classes = layer.labelClasses
        field_name = field.name
        log.debug('Finding occurrences of field {} in label classes'.format(field_name))
        for label_class in label_classes:
            if in_label_class_expression and in_label_class_sql_query:
                break
            if label_class.showClassLabels:
                if not in_label_class_expression and label_class.expression:
                    in_label_class_expression = field_name.lower() in label_class.expression.lower()
                if not in_label_class_sql_query and label_class.SQLQuery:
                    in_label_class_sql_query = field_name.lower() in label_class.SQLQuery.lower()
    return dict(
        in_label_class_expression=in_label_class_expression,
        in_label_class_sql_query=in_label_class_sql_query
    )


def parse_database_from_service_string(database):
    if database != 'n/a':
        pattern = re.compile(r'^(?:sde:\w+\$)?(?:sde:\w+:)(?:\\;\w+=)?([^;:\$]+)[;:\$]?.*$', re.IGNORECASE)
        match = re.match(pattern, database)
        if match:
            database = match.group(1)
    return database


def update_data_sources(mxd_path, data_source_mappings):
    log.info('Updating data sources in MXD: {}'.format(mxd_path))

    mxd = open_mxd(mxd_path)
    for layer in list_layers_in_mxd(mxd):
        if hasattr(layer, 'workspacePath'):
            layer_name = layer.longName if hasattr(layer, 'longName') else layer.name
            for key, value in data_source_mappings.iteritems():
                if fnmatch.fnmatch(layer.workspacePath, key):
                    new_workspace_path = value
                    log.info(
                        'Updating workspace path for layer {}, dataset name: {}, '
                        'current workspace path: {}, new workspace path: {}'
                        .format(layer_name, layer.datasetName, layer.workspacePath, new_workspace_path)
                    )
                    layer.findAndReplaceWorkspacePath(layer.workspacePath, new_workspace_path, False)
                    break
            else:
                log.warn(
                    'No match for layer {}, dataset name: {}, workspace path: {}'
                    .format(layer_name, layer.datasetName, layer.workspacePath)
                )
    mxd.save()


def get_geometry_statistics(dataset_path):
    log.debug('Getting geometry statistics for dataset: {}'.format(dataset_path))

    import arcpy
    desc = arcpy.Describe(dataset_path)
    data_type = desc.dataType

    feature_count = 0
    part_count = 0
    vertex_count = 0

    if data_type == 'Table':
        shape_type = 'n/a'
        feature_count = int(arcpy.GetCount_management(dataset_path).getOutput(0))
    else:
        shape_type = desc.shapeType
        with arcpy.da.SearchCursor(dataset_path, ('SHAPE@',)) as cursor:
            for (shape,) in cursor:
                feature_count += 1
                if shape:
                    part_count += shape.partCount
                    if shape_type == 'Polygon':
                        # Exclude last vertex from each polygon part
                        vertex_count += (shape.pointCount - shape.partCount)
                    else:
                        vertex_count += shape.pointCount

    avg_part_count = part_count / feature_count if feature_count > 0 else 0
    avg_vertex_count = vertex_count / feature_count if feature_count > 0 else 0

    return dict(
        shape_type=shape_type,
        feature_count=feature_count,
        avg_part_count=avg_part_count,
        avg_vertex_count=avg_vertex_count
    )
