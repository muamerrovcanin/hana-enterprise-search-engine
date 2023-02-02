from constants import ENTITY_PREFIX, VIEW_PREFIX
from esh_client import  AttributeView, Column, EshConfiguration, EshObject, EshRequest, Parameter, Query, ResultSetColumn, Rule, RuleSet, SearchRuleSet
import esh_objects

class Constants(object):
    entities = 'entities'
    views = 'views'
    view_name = 'view_name'
    odata_name = 'odata_name'

def map_search_query_filter_comparison(incoming_request_index, model_views, item, main_scope, result_items):
    if 'type' not in item or item['type'] != 'Comparison':
        raise Exception(f"Unexpected item: {item}. It should be Comparison")
    if 'type' in item['property']:
        if item['property']['type'] == esh_objects.Property.__name__:
            property_name = item['property']['property'] if not type(item['property']['property']) is list else ".".join(item['property']['property'])
            found_property = False
            try:
                for column_name, column_definition in model_views[main_scope]['columns'].items():
                    if property_name == ".".join(column_definition['path']):
                        found_property = True
                        item['property']['property'] = column_name
                        if 'comparison_paths' not in result_items:
                            result_items['comparison_paths'] = []
                        # TODO check if it is better via property_name: result_items['comparison_paths'].append(property_name)
                        result_items['comparison_paths'].append(column_definition['path'])
                        break
            except:
                raise Exception(f"Incoming requests [{incoming_request_index}]: Unknown property: {property_name} for scope: {main_scope}")
            if not found_property:
                raise Exception(f"Incoming requests [{incoming_request_index}]: Unknown property: {property_name} for scope: {main_scope}")
        elif item['property']['type'] == esh_objects.Expression.__name__:
            map_search_query_filter_expression(incoming_request_index, model_views, item['property'], main_scope, result_items)
            # raise Exception(f"Incoming requests [{incoming_request_index}]: searchQueryFilter not implemented Comparison -> Property: {item['property']['type']}")
    else:
        property_name = item['property'] 
        found_property = False
        try:
            for column_name, column_definition in model_views[main_scope]['columns'].items():
                if property_name == ".".join(column_definition['path']):
                    found_property = True
                    item['property'] = column_name
                    break
        except:
            raise Exception(f"Incoming requests [{i}]: Unknown property: {property_name} for scope: {main_scope}")
        if not found_property:
            raise Exception(f"Incoming requests [{i}]: Unknown property: {property_name} for scope: {main_scope}")

def map_search_query_filter_expression(incoming_request_index, model_views, item, main_scope, result_items):
    if 'type' not in item or item['type'] != 'Expression':
        raise Exception(f"Unexpected item: {item}. It should be Expression")
    for expression_item in item['items']:
        if 'type' in expression_item:
            if expression_item['type'] == 'Comparison':
                map_search_query_filter_comparison(incoming_request_index, model_views, expression_item, main_scope, result_items)
            elif expression_item['type'] == 'Expression':
                for expression_item_element in expression_item['items']:
                    map_search_query_filter_comparison(incoming_request_index, model_views, expression_item_element, main_scope, result_items)
            else:
                result_items['exist_free_style'] = True
        else:
            result_items['exist_free_style'] = True

def map_search_query_filter(model_views, search_query_filter, result_items):
    if search_query_filter['type'] != esh_objects.Expression.__name__:
        raise Exception(f"Incoming requests [{i}]: searchQueryFilter has to be type Expression, but got: {search_query_filter['type']}")
    for j in range(0, len(search_query_filter['items'])):
        item = search_query_filter['items'][j]
        if type(item) is dict:
            if item['type'] == esh_objects.ScopeComparison.__name__:
                if j != 0:
                    raise Exception(f"Incoming requests [{i}]: searchQueryFilter should have ScopeComparison on the first position, but got on position: {j}")
                for i in range(0, len(item['values'])):
                    scope = item['values'][i]
                    if scope not in model_views:
                        raise Exception(f"Incoming requests [{i}]: searchQueryFilter contains unknown scope: {scope}")
                    item['values'][i] = model_views[scope]['odata_name']
                    main_scope = scope # TODO currently only one main scope allowed, e.g. SCOPE:example.Person
                    result_items['scope'] = main_scope            
            elif item['type'] == esh_objects.Comparison.__name__:
                map_search_query_filter_comparison(i, model_views, item, main_scope, result_items)
            elif item['type'] == esh_objects.Expression.__name__:
                map_search_query_filter_expression(i, model_views, item, main_scope, result_items)
                # raise Exception(f"Incoming requests [{i}]: searchQueryFilter not implemented mapping type: {item['type']}")
        else:
            result_items['exist_free_style'] = True


def map_request(mapping: dict, incoming_requests: list):
    result_items = {}
    for i in range(0, len(incoming_requests)):
        incoming_request = incoming_requests[i]
        incoming_request['select'] = ['ID']
        for key in incoming_request.keys():
            if key == esh_objects.Constants.searchQueryFilter:
                if not incoming_request[esh_objects.Constants.searchQueryFilter]:
                    raise Exception(f"Incoming requests [{i}]: searchQueryFilter cannot be empty")
                # HHH search_query_filter = esh_objects.deserialize_objects(incoming_request[esh_objects.Constants.searchQueryFilter])
                search_query_filter = incoming_request[esh_objects.Constants.searchQueryFilter]
                map_search_query_filter(mapping['views'], search_query_filter, result_items)
    returning_object = {
            'incoming_requests': incoming_requests
    }
    if 'scope' in result_items:
        returning_object['scope'] = result_items['scope']
    if 'comparison_paths' in result_items:
        returning_object['comparison_paths'] = result_items['comparison_paths']
    if 'exist_free_style' in result_items:
        returning_object['exist_free_style'] = result_items['exist_free_style']
    return returning_object

def map_request_to_rule_set_old(schema_name: str, mapping: dict, incoming_request: EshObject):
    query = Query()
    if incoming_request.scope is not None:
        if len(incoming_request.scope) != 1:
            raise Exception("only one element is allowed in the 'scope'")
        scope = incoming_request.scope[0]
        ruleset = RuleSet()
        scope_entity = mapping["entities"][scope]
        table_name = scope_entity["table_name"]
        # view_name = table_name.replace("ENTITY/", "VIEW/") # TODO only temp
        view_name = VIEW_PREFIX + table_name[len(ENTITY_PREFIX):]
        mapping_table = mapping["tables"][table_name]
        if incoming_request.searchQueryFilter is not None:
            for item in incoming_request.searchQueryFilter.items:
                if query.column is None:
                    query.column = []
                property_name = item.property.property[0]
                operator = item.operator
                value = item.value.value

                db_column_name = scope_entity["elements"][property_name]["column_name"]
                # column_fuzziness = mapping_table["columns"][db_column_name]["annotations"]["@Search.fuzzinessThreshold"]
                # if column_fuzziness is None:
                #    column_fuzziness = 0.77
                column_fuzziness = 0.85
                column=Column(
                    name = db_column_name,
                    minFuzziness = column_fuzziness,
                    ifMissingAction = "skipRule"
                )
                ruleset.rule = Rule(name="rule1", columns=[column])

                # print(property_name, operator,value, db_column_name)
                query.column.append(Column(name=db_column_name, value=value))
        primary_key_column = mapping_table["pk"]
        ruleset.attributeView = AttributeView(schema=schema_name,name=view_name,key_column=primary_key_column)
        query.ruleset = [ruleset]
    else:
        raise Exception("missing mandatory parameter 'scope'")
    if incoming_request.top is not None:
        query.limit = incoming_request.top
    if incoming_request.skip is not None:
        query.offset = incoming_request.skip
    if incoming_request.select is not None:
        for select_property in incoming_request.select:
            if query.resultsetcolumn is None:
                query.resultsetcolumn = []
            query.resultsetcolumn.append(ResultSetColumn(name=scope_entity["elements"][select_property.property]["column_name"]))

    return_value = SearchRuleSet(query=query)
    return return_value


def get_view_column_name(property: list[str]):
    return "_".join(list(map(lambda i: i.upper(), property)))

def map_request_to_rule_set(schema_name: str, mapping: dict, incoming_request: EshRequest):
    query = Query()

    if incoming_request.query.scope is not None:
        if len(incoming_request.query.scope) != 1:
            raise Exception("only one element is allowed in the 'scope'")
        scope = incoming_request.query.scope[0]
        ruleset = RuleSet()
        scope_entity = mapping["entities"][scope]
        table_name = scope_entity["table_name"]
        view_name = VIEW_PREFIX + table_name[len(ENTITY_PREFIX):]
        mapping_table = mapping["tables"][table_name]

        if incoming_request.parameters:
            for parameter in incoming_request.parameters:
                print(parameter)
                if query.column is None:
                    query.column = []
                if isinstance(parameter.name, str):
                    db_column_name = parameter.name
                else: # it is Property Object
                    db_column_name = get_view_column_name(parameter.name.property)
                value = parameter.value.value
                query.column.append(Column(name=db_column_name, value=value))


        if incoming_request.rules:
            for rule in incoming_request.rules:
                if ruleset.rules is None:
                    ruleset.rules = []
                rule_columns = []
                for rule_column in rule.columns:
                    db_column_name = get_view_column_name(rule_column.name.property)
                    column=Column(
                        name = db_column_name,
                        minFuzziness = rule_column.minFuzziness if rule_column.minFuzziness is not None else 0.85,
                        ifMissingAction = rule_column.ifMissingAction if rule_column.ifMissingAction is not None else "skipRule"
                    )
                    rule_columns.append(column)
                ruleset.rules.append(Rule(name=rule.name, columns=rule_columns))
        primary_key_column = mapping_table["pk"]
        ruleset.attributeView = AttributeView(schema=schema_name,name=view_name,key_column=primary_key_column)
        query.ruleset = [ruleset]
    else:
        raise Exception("missing mandatory parameter 'scope'")
    if incoming_request.query.top is not None:
        query.limit = incoming_request.query.top
    if incoming_request.query.skip is not None:
        query.offset = incoming_request.query.skip
    if incoming_request.query.select is not None:
        for select_property in incoming_request.query.select:
            if query.resultsetcolumn is None:
                query.resultsetcolumn = []
            db_column_name = get_view_column_name(select_property.property)
            query.resultsetcolumn.append(ResultSetColumn(name=db_column_name))

    return_value = SearchRuleSet(query=query)
    return return_value

def get_view_column_name_from_object(mapping_object: dict, property: list[str]):
    property_name = property[0]
    if "elements" in mapping_object:
        print("it is OBJECT")
        return get_view_column_name_from_object(mapping_object[property_name]['elements'], property[1:])
    elif "items" in mapping_object:
        print("it is ARRAY")
    return mapping_object[property_name]['column_name']

def get_view_column_name_from_array(mapping_object: dict, property: list[str]):
    property_name = property[0]
    if "elements" in mapping_object:
        print("it is OBJECT")
        if len(property) == 1:
            return mapping_object['elements'][property_name]['column_name']
        return get_view_column_name_from_object(mapping_object['elements'][property_name]['elements'], property[1:])
    elif "items" in mapping_object:
        print("it is ARRAY")
    return  mapping_object[property_name]['column_name']


def get_view_column_name_ex(mapping: dict, scope: str, property: list[str]):

    property_name = property[0]
    if "elements" in mapping['entities'][scope]['elements'][property_name]:
        print("it is OBJECT")
        return get_view_column_name_from_object(mapping['entities'][scope]['elements'][property_name]['elements'], property[1:])
    elif "items" in mapping['entities'][scope]['elements'][property_name]:
        print("it is ARRAY")
        #return get_view_column_name_from_array(mapping['entities'][scope]['elements'][property_name]['items'], property[1:], (property_name))
        return property_name.upper() + '_' + get_view_column_name_from_array(mapping['entities'][scope]['elements'][property_name]['items'], property[1:])
    return mapping['entities'][scope]['elements'][property_name]['column_name']

