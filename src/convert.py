"""Mapping between external objects and internal tables using 'tables' as internal runtime-format """
from operator import le
from uuid import uuid1
from name_mapping import NameMapping
import json

ENTITY_PREFIX = 'ENTITY/'
VIEW_PREFIX = 'VIEW/'
PRIVACY_CATEGORY_COLUMN_DEFINITION = ('_PRIVACY_CATEGORY', {'type':'TINY'})
PRIVACY_CATEGORY_ANNOTATION = '@EnterpriseSearchIndex.privacyCategory'

class DefaultPK:
    @staticmethod
    def get_pk(node_name, subnode_level):
        #pylint: disable=unused-argument
        return uuid1().urn[9:]
    @staticmethod
    def get_definition(subnode_level):
        #pylint: disable=unused-argument
        return ('_ID', {'type':'VARCHAR', 'length': 36, 'isIdColumn': True})

class ModelException(Exception):
    pass

class DataException(Exception):
    pass


def get_sql_type(node_name_mapping, cson, cap_type, pk):
    ''' get SQL type from CAP type'''
    if cap_type['type'] in cson['definitions'] and 'type' in cson['definitions'][cap_type['type']]:
        return get_sql_type(node_name_mapping, cson, cson['definitions'][cap_type['type']], pk)

    sql_type = {}
    if 'length' in cap_type:
        sql_type['length'] = cap_type['length']
    match cap_type['type']:
        case 'cds.UUID':
            sql_type['type'] = 'NVARCHAR'
            sql_type['length'] = 36
        case 'cds.String':
            sql_type['type'] = 'NVARCHAR'
            if not 'length' in cap_type:
                sql_type['length'] = 5000
        case 'cds.Integer64':
            sql_type['type'] = 'BIGINT'
        case 'cds.Timestamp':
            sql_type['type'] = 'TIMESTAMP'
        case 'cds.Boolean':
            sql_type['type'] = 'BOOLEAN'
        case 'cds.Date':
            sql_type['type'] = 'DATE'
        case 'cds.Integer':
            sql_type['type'] = 'INTEGER'
        case 'cds.Decimal':
            sql_type['type'] = 'DECIMAL'
            if 'precision' in cap_type:
                sql_type['precision'] = cap_type['precision']
            if 'scale' in cap_type:
                sql_type['scale'] = cap_type['scale']
        case 'cds.Time':
            sql_type['type'] = 'TIME'
        case 'cds.DateTime':
            sql_type['type'] = 'DATETIME'
        case 'cds.Association':
            target_key_property = \
                cson['definitions'][cap_type['target']]['elements'][cson['definitions'][cap_type['target']]['pk']]
            sql_type = get_sql_type(node_name_mapping, cson, target_key_property, pk)
            rel = {}
            rel_to, _ = node_name_mapping.register([cap_type['target']], ENTITY_PREFIX)
            rel['table_name'] = rel_to
            rel['type'] = 'association'
            if 'cardinality' in cap_type:
                rel['cardinality'] = cap_type['cardinality']
            sql_type['rel'] = rel
        case _:
            print(cap_type['type'])
            if cap_type['type'].startswith(cson['namespace']):
                rep_type = find_definition(cson, cap_type)
                print(rep_type)
                sql_type['type'] = get_sql_type(node_name_mapping, cson, cson['definitions'][rep_type['type']], pk)
            else:
                None #pylint: disable=pointless-statement
            t = cap_type['type']
            print(f'Unexpected type: {t}')
            raise ModelException(f'Unexpected cds type {t}')

    # Copy annotations
    annotations = {k:v for k,v in cap_type.items() if k.startswith('@')}
    if annotations:
        sql_type['annotations'] = annotations

    return sql_type


def find_definition(cson, type_definition):
    found = False
    while not found:
        if 'type' in type_definition and type_definition['type'] in cson['definitions']\
             and (('type' in cson['definitions'][type_definition['type']] \
                 and cson['definitions'][type_definition['type']]['type'] in cson['definitions']) \
                     or 'elements' in  cson['definitions'][type_definition['type']]):
            type_definition = cson['definitions'][type_definition['type']]
        else:
            found = True
    return type_definition

def get_key_columns(subnode_level, pk):
    d = pk.get_definition(subnode_level)
    if subnode_level == 0:
        res = (d[0], None, {d[0]: d[1]})
    elif subnode_level == 1:
        pk_name = d[0] + str(subnode_level)
        pk_parent_name = d[0]
        res = (pk_name, pk_parent_name, {pk_parent_name: d[1], pk_name: d[1]})
    else:
        pk_name = d[0] + str(subnode_level)
        pk_parent_name = d[0] + str(subnode_level - 1)
        res = (pk_name, pk_parent_name, {pk_parent_name: d[1], pk_name: d[1]})
    return res

def add_key_columns_to_node(node, subnode_level, pk):
    d = pk.get_definition(subnode_level)
    if subnode_level == 0:
        raise NotImplementedError
    elif subnode_level == 1:
        pk_name = d[0] + str(subnode_level)
        pk_parent_name = d[0]
        key_properties = {pk_parent_name: d[1], pk_name: d[1]}
    else:
        pk_name = d[0] + str(subnode_level)
        pk_parent_name = d[0] + str(subnode_level - 1)
        key_properties = {pk_parent_name: d[1], pk_name: d[1]}
    node['pk'] = pk_name
    node['pkParent'] = pk_parent_name
    node['properties'] = key_properties




def cson_entity_to_subnodes(element_name_ext, element, node, property_name_mapping,
    node_name_mapping, cson, nodes, path, type_name, subnode_level, parent_table_name,
    sur_node, sur_prop_name_mapping, sur_prop_path, ext_int):
    _ = cson_entity_to_nodes(node_name_mapping, cson, nodes, path + [type_name],\
        element_name_ext, element, subnode_level, False, parent_table_name = parent_table_name,
        sur_node = sur_node, sur_prop_name_mapping = sur_prop_name_mapping, 
        sur_prop_path = sur_prop_path, ext_int=ext_int)

def cson_entity_to_nodes(node_name_mapping, cson, nodes, path, type_name, type_definition,\
    subnode_level = 0, is_table = True, has_pc = False, pk = DefaultPK, parent_table_name = None,
    sur_node = None, sur_prop_name_mapping = None, sur_prop_path = [], ext_int = {}):
    ''' Transforms cson entity definition to model definition.
    The nodes links the external object-oriented-view with internal HANA-database-view.'''
    external_path = path + [type_name]
    if sur_node:
        node = sur_node
        property_name_mapping = sur_prop_name_mapping
    else:
        node = {'external_path':external_path, 'level': subnode_level}
        property_name_mapping = NameMapping()
        if parent_table_name:
            node['parent'] = parent_table_name
        if subnode_level == 0:
            annotations = {k:v for k,v in type_definition.items() if k.startswith('@')}
            if annotations:
                node['annotations'] = annotations
        if is_table:
            if subnode_level == 0:
                pk_property_name, _ = property_name_mapping.register([type_definition['pk']])
                ext_int['elements'][type_definition['pk']] = {'column_name': pk_property_name}
                node['pk'] = pk_property_name
                table_name, node_map = node_name_mapping.register(external_path, ENTITY_PREFIX\
                    , definition = {'pk': pk_property_name})
                ext_int['table_name'] = table_name
                node['properties'] = {}
            else:
                table_name, node_map = node_name_mapping.register(external_path)
                ext_int['table_name'] = table_name
                add_key_columns_to_node(node, subnode_level, pk)
            node['table_name'] = table_name
            parent_table_name = table_name
        #if has_pc:
        #    node['properties'][PRIVACY_CATEGORY_COLUMN_DEFINITION[0]] = PRIVACY_CATEGORY_COLUMN_DEFINITION[1]
    #else:
    #    node = {'properties': {}}
    subnodes = []
    type_definition = find_definition(cson, type_definition) # ToDo: check, if needed
    if type_definition['kind'] == 'entity' or (path and 'elements' in type_definition):
        for element_name_ext, element in type_definition['elements'].items():
            is_virtual = '@sap.esh.isVirtual' in element and element['@sap.esh.isVirtual']
            is_association = 'type' in element and element['type'] == 'cds.Association'
            ext_int['elements'][element_name_ext] = {}
            if is_virtual:
                if not is_association:
                    raise ModelException(f'{element_name_ext}: '
                    'Annotation @sap.esh.isVirtual is only allowed on associations')
                if subnode_level != 0:
                    raise ModelException(f'{element_name_ext}: '
                    'Annotation @sap.esh.isVirtual is only allowed on root level')
                referred_element = element['target']
                backward_rel = [k for k, v in cson['definitions'][referred_element]['elements'].items()\
                     if 'type' in v and v['type'] == 'cds.Association' and v['target'] == type_name]
                if len(backward_rel) != 1:
                    raise ModelException(f'{element_name_ext}: Annotation @sap.esh.isVirtual is only allowed if '
                    f'exactly one backward association exists from referred entity {referred_element}',)
                element['isVirtual'] = True
            if is_association:
                element['target_table_name'], _ = node_name_mapping.register([element['target']], ENTITY_PREFIX)
                element['target_pk'] = cson['definitions'][element['target']]['pk']
                element_name, _ = property_name_mapping.register(sur_prop_path + [element_name_ext], definition=element)
                ext_int['elements'][element_name_ext]['definition'] = element
            else:
                element_name, _ = property_name_mapping.register(sur_prop_path + [element_name_ext])
                
            element_needs_pc = PRIVACY_CATEGORY_ANNOTATION in element
            if 'items' in element or element_needs_pc: # collection (many keyword)
                if 'items' in element and 'elements' in element['items']: # nested definition
                    sub_type = element['items']
                    sub_type['kind'] = 'type'
                elif 'items' in element and element['items']['type'] in cson['definitions']:
                    sub_type = cson['definitions'][element['items']['type']]
                else: # built-in type
                    if 'items' in element:
                        sub_type = element['items']
                        sub_type['kind'] = 'type'
                    else:
                        sub_type = element
                        sub_type['kind'] = 'type'
                ext_int['elements'][element_name_ext]['items'] = {'elements': {}}
                subnode = cson_entity_to_nodes(node_name_mapping, cson, nodes, path +\
                    [type_name], element_name_ext, sub_type, subnode_level +  1, True\
                    , element_needs_pc, parent_table_name = parent_table_name
                    , ext_int= ext_int['elements'][element_name_ext]['items'])
                subnodes.append(subnode)
                node['properties'][element_name] = {'rel': {'table_name':subnode['table_name'],\
                    'type':'containment'}, 'external_path': sur_prop_path + [element_name_ext], 'isVirtual': True}
            elif 'type' in element:
                if element['type'] in cson['definitions']:
                    if 'elements' in cson['definitions'][element['type']]:
                        ext_int['elements'][element_name_ext]['elements'] = {}
                        cson_entity_to_subnodes(element_name_ext, element, node, property_name_mapping,
                            node_name_mapping, cson, nodes, path, type_name, subnode_level, 
                            parent_table_name = parent_table_name, sur_node=node, 
                            sur_prop_name_mapping=property_name_mapping,
                            sur_prop_path=sur_prop_path + [element_name_ext],
                            ext_int=ext_int['elements'][element_name_ext])
                    else:
                        node['properties'][element_name] =\
                            get_sql_type(node_name_mapping, cson, cson['definitions'][element['type']], pk)
                        node['properties'][element_name]['external_path'] = sur_prop_path + [element_name_ext]
                        ext_int['elements'][element_name_ext]['column_name'] = element_name
                else:
                    node['properties'][element_name] = get_sql_type(node_name_mapping, cson, element, pk)
                    node['properties'][element_name]['external_path'] = sur_prop_path + [element_name_ext]
                    ext_int['elements'][element_name_ext]['column_name'] = element_name
            elif 'elements' in element: # nested definition
                element['kind'] = 'type'
                ext_int['elements'][element_name_ext]['elements'] = {}
                cson_entity_to_subnodes(element_name_ext, element, node, property_name_mapping,
                    node_name_mapping, cson, nodes, path, type_name, subnode_level, 
                    parent_table_name=parent_table_name, sur_node=node, 
                    sur_prop_name_mapping=property_name_mapping,
                    sur_prop_path=sur_prop_path + [element_name_ext],
                    ext_int=ext_int['elements'][element_name_ext])

            else:
                raise NotImplementedError
    elif path and type_definition['kind'] == 'type': # single property for one node
        ext_int['table_name'] = table_name
        ext_int['column_name'] = '_VALUE'
        if not type_definition['type'] in cson['definitions']:
            node['properties']['_VALUE'] = get_sql_type(node_name_mapping, cson, type_definition, pk)
        #elif '@EnterpriseSearchIndex.type' in cson['definitions'][type_definition['type']] and\
        #    cson['definitions'][type_definition['type']]['@EnterpriseSearchIndex.type'] == 'CodeList':
            # this is for codelist TODO, change this harcoded value
        #    node['properties']["_VALUE"] = {'type': "NVARCHAR", 'length': 50}
        else:
            # print("----- {}={}".format(path, type_definition['type']))
            # print(cson['definitions'][type_definition['type']])
            #found = False
            #while not found:
            #    if 'type' in type_definition and type_definition['type'] in cson['definitions'] and 'type' in\
            #        cson['definitions'][type_definition['type']] and \
            #            cson['definitions'][type_definition['type']]['type'] in cson['definitions']:
            #        type_definition = cson['definitions'][type_definition['type']]
            #    else:
            #        found = True
            # HERE type_definition = find_definition(cson, type_definition)
            # if 'elements' in cson['definitions'][type_definition['type']]:
            if 'elements' in type_definition:
                for key, value in type_definition['elements'].items():
                    # print("KEY: {}, value: {}, find_definition".format(key, value),find_definition(value) )
                    node['properties'][key] = get_sql_type(node_name_mapping, cson, find_definition(cson, value), pk)
            else:
                node['properties']['_VALUE'] = get_sql_type(node_name_mapping, cson, type_definition, pk)
            #node['properties']['ONE'] = 2
    else:
        raise NotImplementedError

    if subnodes:
        node['contains'] = [w['table_name'] for w in subnodes]
    if is_table:
        if 'contains' in property_name_mapping.ext_tree:
            node_map['properties'] = property_name_mapping.ext_tree['contains']
        else:
            node_map['properties'] = {}
        nodes[table_name] = node
    return node


def is_many_rel(property_rel):
    return 'cardinality' in property_rel\
        and 'max' in property_rel['cardinality'] and property_rel['cardinality']['max'] == '*'

def cson_to_mapping(cson, pk = DefaultPK):
    nodes = {}
    ext_int_def = {}
    node_name_mapping = NameMapping()
    for name, definition in cson['definitions'].items():
        if definition['kind'] == 'entity':
            keys = [k for k, v in definition['elements'].items() if 'key' in v and v['key']]
            if len(keys) != 1:
                raise ModelException(f'{name}: An entity must have exactly one key property')
            definition['pk'] = keys[0]
    for name, definition in cson['definitions'].items():
        if definition['kind'] == 'entity':
            ext_int = {'elements':{}}
            cson_entity_to_nodes(node_name_mapping, cson, nodes, [], name, definition, pk = pk, ext_int = ext_int)
            ext_int_def[name] = ext_int


    for node_name, node in nodes.items():
        for prop_name, prop in node['properties'].items():
            is_virtual = 'annotations' in prop and '@sap.esh.isVirtual' in prop['annotations'] and \
                prop['annotations']['@sap.esh.isVirtual']
            is_association = 'rel' in prop and prop['rel']['type'] == 'association'
            if is_virtual:
                if not is_association:
                    raise ModelException(f'{prop_name}: Annotation @sap.esh.isVirtual is only allowed on associations')
                if node['level'] != 0:
                    raise ModelException(f'{prop_name}: Annotation @sap.esh.isVirtual is only allowed on root level')
                referred_node = nodes[prop['rel']['table_name']]
                backward_rel = [(r, is_many_rel(r['rel'])) for r in referred_node['properties'].values() \
                    if 'rel' in r and r['rel']['table_name'] == node_name]
                if len(backward_rel) != 1:
                    msg = ( f'{prop_name}: Annotation @sap.esh.isVirtual is only '
                    'allowed if exactly one backward association exists from referred entity ')
                    msg += referred_node['externalPath'][0]
                    raise ModelException(msg)
                prop['isVirtual'] = True

        node['sql'] = {}
        table_name = node['table_name']
        nl = node['level']
        if nl <= 1:
            if nl == 0:
                key_column = node['pk']
            else:
                key_column = node['pkParent']
            select_columns = [f'"{k}"' for k, v in node['properties'].items() if not ('isVirtual' in v and v['isVirtual'])]
            sql_table_joins = f'"{table_name}"'
            sql_condition = f'"{key_column}" in ({{id_list}})'
            node['sql']['delete'] = f'DELETE from {sql_table_joins} where {sql_condition}'
        else:
            select_columns = [f'L{nl}."{k}"' for k, v in node['properties'].items() if not ('isVirtual' in v and v['isVirtual'])]
            joins = []
            del_subselect = []
            parents = get_parents(nodes, node, node['level'] - 1)
            for i, parent in enumerate(parents):
                joins.append(f'inner join "{parent}" L{i+1} on L{i+2}._ID{i+1} = L{i+1}._ID{i+1}')
                if i == len(parents) - 1:
                    del_subselect.append(f'select _ID{i+1} from "{parent}" L{i+1}')
                else:
                    del_subselect.append(f'inner join "{parent}" L{i+1} on L{i+2}._ID{i+1} = L{i+1}._ID{i+1}')
            joins.reverse()
            del_subselect.reverse()
            del_subselect.append('where L1."_ID" in ({id_list})')
            del_subselect_str = ' '.join(del_subselect)
            sql_table_joins = f'"{table_name}" L{nl} {" ".join(joins)}'
            sql_condition = f'L1."_ID" in ({{id_list}})'
            node['sql']['delete'] = f'DELETE from "{table_name}" where _ID{len(parents)} in ({del_subselect_str})'

        node['sql']['select'] = f'SELECT {", ".join(select_columns)} from {sql_table_joins} where {sql_condition}'

    #return {'tables': nodes, 'index': node_name_mapping.ext_tree['contains'], 'entities': ext_int_def}
    return {'tables': nodes, 'entities': ext_int_def}


def get_parents(nodes, node, steps):
    if not 'parent' in node:
        return []
    parent = node['parent']
    if steps == 1:
        return [parent]
    else:
        return get_parents(nodes, nodes[parent], steps - 1) + [parent]

def array_to_dml(inserts, objects, subnode_level, parent_object_id, pk, ext_int):
    full_table_name = ext_int['table_name']
    if not full_table_name in inserts:
        _, _, key_columns = get_key_columns(subnode_level, pk)
        key_col_names = {k:idx for idx, k in enumerate(key_columns.keys())}
        inserts[full_table_name] = {'columns': key_col_names, 'rows':[]}
        inserts[full_table_name]['columns']['_VALUE'] = 2
    for obj in objects:
        row = []
        row.append(parent_object_id)
        object_id = pk.get_pk(full_table_name, subnode_level)
        row.append(object_id)
        row.append(obj)
        inserts[full_table_name]['rows'].append(row)


def object_to_dml(nodes, inserts, objects, idmapping, subnode_level = 0, col_prefix = [],\
    parent_object_id = None, propagated_row = None, propagated_object_id = None, pk = DefaultPK
    , ext_int = {}, parent_table_name = ''):
    if 'table_name' in ext_int:
        full_table_name = ext_int['table_name']
    else:
        full_table_name = parent_table_name
    for obj in objects:
        if subnode_level == 0 and 'id' in obj:
            raise DataException('id is a reserved property name')
        if propagated_row is None:
            row = []
            if parent_object_id:
                row.append(parent_object_id)
            object_id = pk.get_pk(full_table_name, subnode_level)
            if subnode_level == 0:
                if nodes['tables'][full_table_name]['pk'] == 'ID':
                    obj['id'] = object_id
                if 'source' in obj:
                    for source in obj['source']:
                        hashable_key = json.dumps(source)
                        if hashable_key in idmapping:
                            idmapping[hashable_key]['resolved'] = True
                        else:
                            idmapping[hashable_key] = {'id':object_id, 'resolved':True}
            else:
                row.append(object_id)
                if not full_table_name in inserts:
                    _, _, key_columns = get_key_columns(subnode_level, pk)
                    key_col_names = {k:idx for idx, k in enumerate(key_columns.keys())}
                    inserts[full_table_name] = {'columns': key_col_names, 'rows':[]}
            if not full_table_name in inserts:
                inserts[full_table_name] = {'columns': {}, 'rows':[]}
            else:
                row.extend([None]*(len(inserts[full_table_name]['columns']) - len(row)))
        else:
            row = propagated_row
            object_id = propagated_object_id

        for k, v in obj.items():
            value = None
            if not 'elements' in ext_int:
                pass
            if k in ext_int['elements']:
                #prop = properties[k]
                #if prop != ext_int['elements'][k]:
                #    pass
                prop = ext_int['elements'][k]
                if 'definition' in prop and 'type' in prop['definition']\
                    and prop['definition']['type'] == 'cds.Association':
                    if 'isVirtual' in prop['definition'] and prop['definition']['isVirtual']:
                        raise DataException(f'Data must not be provided for virtual property {k}')
                    if prop['definition']['target_pk'] in v:
                        value = v[prop['definition']['target_pk']]
                    elif 'source' in v:
                        if isinstance(v['source'], list):
                            hashable_keys = set([json.dumps(w) for w in v['source']])
                            if len(hashable_keys) == 0:
                                raise DataException(f'Association property {k} has no source')
                            elif len(hashable_keys) > 1:
                                raise DataException(f'Association property {k} has conflicting sources')
                            hashable_key = list(hashable_keys)[0]
                            if hashable_key in idmapping:
                                value = idmapping[hashable_key]['id']
                            else:
                                target_table_name = prop['definition']['target_table_name']
                                value = pk.get_pk(target_table_name, 0)
                                idmapping[hashable_key] = {'id':value, 'resolved':False}
                        else:
                            raise DataException(f'Association property {k} is not a list')
                    else:
                        raise DataException(f'Association property {k} has no source property')
            else:
                raise DataException(f'Unknown property {k}')
            if value is None and isinstance(v, list):
                if not 'items' in ext_int['elements'][k]:
                    raise DataException(f'{k} is not an array property')
                if ext_int['elements'][k]['items']['elements']:
                    object_to_dml(nodes, inserts, v, idmapping, subnode_level + 1,\
                        parent_object_id = object_id, pk = pk, 
                        ext_int=ext_int['elements'][k]['items'], parent_table_name=full_table_name)
                else:
                    array_to_dml(inserts, v, subnode_level + 1, object_id, pk
                    , ext_int=ext_int['elements'][k]['items'])
            elif value is None and isinstance(v, dict):
                object_to_dml(nodes, inserts, [v], idmapping, subnode_level, col_prefix + [k],\
                    propagated_row = row, propagated_object_id=object_id
                    , pk = pk, 
                    ext_int=ext_int['elements'][k], parent_table_name=full_table_name)
            else:
                column_name = ext_int['elements'][k]['column_name']
                if not value:
                    value = v
                if not column_name in inserts[full_table_name]['columns']:
                    inserts[full_table_name]['columns'][column_name] = len(inserts[full_table_name]['columns'])
                    row.append(value)
                else:
                    row[inserts[full_table_name]['columns'][column_name]] = value
        if row and not propagated_row and full_table_name in inserts:
            inserts[full_table_name]['rows'].append(row)


def objects_to_dml(nodes, objects, pk = DefaultPK):
    inserts = {}
    idmapping = {}
    for object_type, objects in objects.items():
        if not object_type in nodes['entities']:
            raise DataException(f'Unknown object type {object_type}')
        object_to_dml(nodes, inserts, objects, idmapping, pk = pk,
            ext_int=nodes['entities'][object_type])
    if idmapping:
        dangling = [json.loads(k) for k, v in idmapping.items() if not v['resolved']]
        if dangling:
            # ToDo: Handle references to objects which are not in one data package
            raise DataException('References to objects outside of one data package '
            f'is not yet supported. No object exists with source {json.dumps(dangling)}')
    for v in inserts.values():
        length = len(v['columns'])
        for row in v['rows']:
            if len(row) < length:
                row.extend([None]*(length - len(row)))

    return {'inserts': inserts}
