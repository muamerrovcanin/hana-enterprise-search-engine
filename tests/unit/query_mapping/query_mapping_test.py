import unittest
import json
import query_mapping

class TestQueryMapping(unittest.TestCase):

    def test_get_annotations_serialized(self):
        a = {
                "@Search": {
                    "searchable": True, 
                    "abc": 123,
                    "l1": {
                        "l2-1": "something",
                        "l2-2": [
                            {
                                "bbb": "ccc"
                            }
                        ]
                    }
                },
                "@EnterpriseSearch": {
                    "searchable": True, 
                    "abc": 234
                }
            }
        serialized_annotations = query_mapping.get_annotations_serialized(a)
        # print(json.dumps(a, indent=4))
        # print(json.dumps(serialized_annotations, indent = 4))
        expected_result = {
                "@Search.searchable": True,
                "@Search.abc": 123,
                "@Search.l1.l2-1": "something",
                "@Search.l1.l2-2": [
                    {
                        "bbb": "ccc"
                    }
                ],
                "@EnterpriseSearch.searchable": True,
                "@EnterpriseSearch.abc": 234
            }
        self.assertEqual(serialized_annotations, expected_result)
    
    def test_get_annotations_deserialized(self):
        a = {
                "@EnterpriseSearch.l11.l111": "--EnterpriseSearch--l11--l111",
                "@Search.l11.l111": "--Search--l11--l111",
                "@Search.l12.l121": "--Search--l12--l121",
                "@Search.l11.l112": "--Search--l11--l112",
                "@EnterpriseSearch.l11.l112": "--EnterpriseSearch--l11--l112",
                "@Search.l12.l122": "--Search--l12--l122",
                "@EnterpriseSearch.l12.l121": "--EnterpriseSearch--l12--l121",
                "@Search.l11.l113": "--Search--l11--l113",
                "@EnterpriseSearch.l13.l131": 1,
                "@EnterpriseSearch.l13.l132": False,
                "@EnterpriseSearch.l13.l133": [{"a":"b"}],
                "@EnterpriseSearch.l13.l134": {"c":"d"}
            }
        serialized_annotations = query_mapping.get_annotations_deserialized(a)
        print(json.dumps(a, indent=4))
        print(json.dumps(serialized_annotations, indent = 4))
        expected_result = {
                "@Search.searchable": True,
                "@Search.abc": 123,
                "@Search.l1.l2-1": "something",
                "@Search.l1.l2-2": [
                    {
                        "bbb": "ccc"
                    }
                ],
                "@EnterpriseSearch.searchable": True,
                "@EnterpriseSearch.abc": 234
            }
        # self.assertEqual(serialized_annotations, expected_result)


if __name__ == '__main__':
    unittest.main()