'''
External to internal mapping of query
'''
import esh_client as esh

def _extract_property_object(prop, pathes):
    if isinstance(prop, str):
        pathes[(prop,)] = ''
    else:
        pathes[tuple(prop)] = ''

def _extract_property_path(obj, pathes):
    if isinstance(obj, list):
        for o in obj:
            _extract_property_path(o, pathes)
    else:
        match type(obj):
            case esh.Property:
                _extract_property_object(obj.property, pathes)
            case esh.OrderBy:
                _extract_property_object(obj.key.property, pathes)
            case esh.Expression:
                _extract_property_path(obj.items, pathes)
            case esh.UnaryExpression:
                _extract_property_path(obj.item, pathes)
            case esh.Comparison:
                _extract_property_object(obj.property.property, pathes)

def extract_pathes(query: esh.EshObject):
    pathes = {tuple(['id']):''}
    if query.orderby:
        _extract_property_path(query.orderby, pathes)
    if query.select:
        _extract_property_path(query.select, pathes)
    if query.searchQueryFilter:
        _extract_property_path(query.searchQueryFilter.items, pathes)
    return pathes


def _map_property_object(prop, pathes):
    # if isinstance(prop.property, str):
    #    prop.property = pathes[(prop.property,)]
    # else:
    #    prop.property = pathes[tuple(prop.property)]
    prop.property = [pathes[tuple(prop.property)]]



def _map_property(obj, pathes):
    if isinstance(obj, list):
        for o in obj:
            _map_property(o, pathes)
    else:
        match type(obj):
            case esh.Property:
                _map_property_object(obj, pathes)
            case esh.OrderBy:
                _map_property_object(obj.key, pathes)
            case esh.Expression:
                _map_property(obj.items, pathes)
            case esh.UnaryExpression:
                _map_property(obj.item, pathes)
            case esh.Comparison:
                _map_property_object(obj.property, pathes)

def map_query(query, pathes):
    if query.orderby:
        _map_property(query.orderby, pathes)
    if query.select:
        _map_property(query.select, pathes)
    if query.searchQueryFilter:
        _map_property(query.searchQueryFilter.items, pathes)

def get_annotations_serialized(annotation: dict, path: list[str] = []):
    # IN { "@Search": { "enabled": true}}
    # OUT { "@Search.enabled": true}
    serialized_annotations = {}
    if annotation:
        for k, v in annotation.items():
            if k.startswith("@") or len(path) > 0:
                if isinstance(v, dict):
                    serialized_annotations = serialized_annotations | get_annotations_serialized(v, path + [k])
                else:
                    serialized_annotations[".".join(path + [k])] = v
    return serialized_annotations

def get_annotations_deserialized(annotation: dict) -> dict:
    # IN { "@Search.enabled": true}
    # OUT { "@Search": { "enabled": true}}
    deserialized_annotations = {}
    if annotation:
        for k, v in annotation.items():
            path = k.split(".")
            active_object = None
            for i in range(len(path)):
                if i == 0:
                    active_object = deserialized_annotations
                else:
                    active_object = active_object[path[i-1]]
                if i == len(path) - 1:
                    active_object[path[i]] = v
                else:
                    if path[i] not in active_object:
                        active_object[path[i]] = {}
    return deserialized_annotations

def get_nested_object(data: dict, path: list[str]):
    local_data = data
    for path_element in path:
        if path_element in local_data:
            local_data = local_data[path_element]
        else:
            return None 
    return local_data

def set_nested_property(data: dict, path: list[str], value):
    local_data = data
    new_data = None
    for idx, path_element in enumerate(path):
        if idx < len(path) - 1:
            if path_element in local_data:
                local_data = local_data[path_element]
            else:
                new_data = data
                for j in range(idx):
                    new_data = new_data[path[j]]
                new_data[path_element] = {}
                local_data = new_data[path_element]
                

        else:
            local_data[path_element] = value 
    return data
