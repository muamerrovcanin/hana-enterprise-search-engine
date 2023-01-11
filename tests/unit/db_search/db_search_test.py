import unittest
import json
import db_search

class TestStringMethods(unittest.TestCase):


    mapping_rule_set_definition= '''
    {
	"tables": {
		"ENTITY/DOCUMENT": {
			"external_path": [
				"Document"
			],
			"level": 0,
			"pk": "ID",
			"columns": {
				"ID": {
					"type": "NVARCHAR",
					"length": 36,
					"external_path": [
						"id"
					]
				},
				"IMAGE": {
					"type": "NCLOB",
					"external_path": [
						"image"
					]
				},
				"TITLE": {
					"length": 5000,
					"type": "NVARCHAR",
					"annotations": {
						"@sap.esh.isText": true
					},
					"external_path": [
						"title"
					]
				},
				"AUTHOR": {
					"type": "NVARCHAR",
					"length": 5000,
					"annotations": {
						"@sap.esh.isText": true
					},
					"external_path": [
						"author"
					]
				},
				"TEXT": {
					"type": "BLOB",
					"annotations": {
						"@sap.esh.isText": true
					},
					"external_path": [
						"text"
					]
				},
				"CREATEDAT": {
					"type": "DATE",
					"external_path": [
						"createdAt"
					]
				},
				"CHANGEDAT": {
					"type": "DATE",
					"external_path": [
						"changedAt"
					]
				},
				"DOCTYPE": {
					"length": 10,
					"type": "NVARCHAR",
					"external_path": [
						"docType"
					]
				},
				"DOCURL": {
					"type": "NVARCHAR",
					"length": 5000,
					"external_path": [
						"docURL"
					]
				}
			},
			"table_name": "ENTITY/DOCUMENT",
			"sql": {
                "delete": "DELETE from \\\"_schema_name_\\\".\\\"ENTITY/DOCUMENT\\\" where \\\"ID\\\" in (1,2,3)",
				"select": "SELECT \\\"ID\\\", \\\"IMAGE\\\", \\\"TITLE\\\", \\\"AUTHOR\\\", \\\"TEXT\\\", \\\"CREATEDAT\\\", \\\"CHANGEDAT\\\", \\\"DOCTYPE\\\", \\\"DOCURL\\\" from \\\"_schema_name_\\\".\\\"ENTITY/DOCUMENT\\\" where \\\"ID\\\" in (1,2,3)"
				}
		}
	},
	"entities": {
		"Document": {
			"elements": {
				"id": {
					"column_name": "ID"
				},
				"image": {
					"column_name": "IMAGE",
					"annotations": {
						"@UI.Identification": [{
							"Position": 10
						}],
						"@Search.defaultSearchElement": false,
						"@Semantics.imageURL": true,
						"@SAP.Common.Label": "Image"
					}
				},
				"title": {
					"column_name": "TITLE",
					"annotations": {
						"@UI.Identification": [{
							"Position": 30
						}],
						"@EnterpriseSearch.defaultValueSuggestElement": true,
						"@Search.fuzzinessThreshold": 0.85,
						"@Search.defaultSearchElement": true,
						"@SAP.Common.Label": "Title"
					}
				},
				"author": {
					"column_name": "AUTHOR",
					"annotations": {
						"@UI.Identification": [{
							"Position": 90
						}],
						"@Search.defaultSearchElement": true,
						"@SAP.Common.Label": "Author"
					}
				},
				"text": {
					"column_name": "TEXT",
					"annotations": {
						"@UI.Identification": [{
							"Position": 50
						}],
						"@EnterpriseSearch.snippets.enabled": true,
						"@EnterpriseSearch.snippets.maximumLength": 800,
						"@Search.defaultSearchElement": true,
						"@SAP.Common.Label": "Text"
					}
				},
				"createdAt": {
					"column_name": "CREATEDAT",
					"annotations": {
						"@UI.Identification": [{
							"Position": 60
						}],
						"@EnterpriseSearch.filteringFacet.default": true,
						"@SAP.Common.Label": "Created At"
					}
				},
				"changedAt": {
					"column_name": "CHANGEDAT",
					"annotations": {
						"@UI.Identification": [{
							"Position": 70
						}],
						"@EnterpriseSearch.filteringFacet.default": true,
						"@SAP.Common.Label": "Changed At"
					}
				},
				"docType": {
					"column_name": "DOCTYPE",
					"annotations": {
						"@UI.Identification": [{
							"Position": 80
						}],
						"@Search.defaultSearchElement": true,
						"@SAP.Common.Label": "Document type"
					}
				},
				"docURL": {
					"column_name": "DOCURL",
					"annotations": {
						"@UI.Identification": [{
							"Position": 100
						}],
						"@Search.defaultSearchElement": true,
						"@SAP.Common.Label": "Document URL"
					}
				}
			},
			"annotations": {
				"@EnterpriseSearch.enabled": true,
				"@EnterpriseSearchHana.passThroughAllAnnotations": true,
				"@SAP.Common.Label": "Document"
			},
			"table_name": "ENTITY/DOCUMENT"
		}
	}
}
    '''


    def test_phrase(self):
        cv = db_search.ColumnView(json.loads(self.mapping_rule_set_definition), "Document", "__SCHEMA_PLACEHOLDER__", True)
        cv.by_default()
        view_ddl, esh_config = cv.data_definition()
        # cv = db_search._get_column_view(json.loads(self.mapping_rule_set_definition), "example.Person", "PLCSCHEMA", ["firstName"])
        # print(cv.column_name_by_path(["firstName"]))
        self.assertEqual(esh_config['method'], "PUT")
        
    ''' 
    def test_isupper(self):
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())

    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)
    '''
if __name__ == '__main__':
    unittest.main()