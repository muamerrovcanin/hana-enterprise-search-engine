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
        # print(json.dumps(a, indent=4))
        # print(json.dumps(serialized_annotations, indent = 4))
        expected_result = {
            "@EnterpriseSearch": {
                "l11": {
                    "l111": "--EnterpriseSearch--l11--l111",
                    "l112": "--EnterpriseSearch--l11--l112"
                },
                "l12": {
                    "l121": "--EnterpriseSearch--l12--l121"
                },
                "l13": {
                    "l131": 1,
                    "l132": False,
                    "l133": [
                        {
                            "a": "b"
                        }
                    ],
                    "l134": {
                        "c": "d"
                    }
                }
            },
            "@Search": {
                "l11": {
                    "l111": "--Search--l11--l111",
                    "l112": "--Search--l11--l112",
                    "l113": "--Search--l11--l113"
                },
                "l12": {
                    "l121": "--Search--l12--l121",
                    "l122": "--Search--l12--l122"
                }
            }
        }
        self.assertEqual(serialized_annotations, expected_result)

    def test_get_nested_object(self):
        data = {
                "@EnterpriseSearch": {
                    "l1": {
                        "l2": [
                            "a",
                            "b"
                        ]
                    }
                }
            }
        nested_object = query_mapping.get_nested_object(data, ['@EnterpriseSearch', 'l1', 'l2'])
        self.assertEqual(nested_object, ['a', 'b'])

        nested_object_1 = query_mapping.get_nested_object(data, ['@SomethingStrange'])
        self.assertIsNone(nested_object_1)

        nested_object_2 = query_mapping.get_nested_object(data, ['@EnterpriseSearch', 'SomethingStrange'])
        self.assertIsNone(nested_object_2)

    def test_set_nested_property(self):
        data = {}
        nested_object = query_mapping.set_nested_property(data, ['l1'], 123)
        self.assertEqual(nested_object, {'l1': 123})

        nested_object_1 = query_mapping.set_nested_property(data, ['l2', 'l2-1'], "abc")
        self.assertEqual(nested_object_1, {'l1': 123, 'l2': {'l2-1': "abc"}})

        nested_object_2 = query_mapping.set_nested_property(data, ['l2', 'l2-2'], True)
        self.assertEqual(nested_object_2, {'l1': 123, 'l2': {'l2-1': "abc", 'l2-2': True}})

        nested_object_3 = query_mapping.set_nested_property(data, ['l3'], 456)
        self.assertEqual(nested_object_3, {'l1': 123, 'l2': {'l2-1': "abc", 'l2-2': True}, 'l3': 456})

        nested_object_3 = query_mapping.set_nested_property(data, ['l4', 'l4-1', 'l4-1-1'], ["aa", "bb"])
        self.assertEqual(nested_object_3, {'l1': 123, 'l2': {'l2-1': "abc", 'l2-2': True}, 'l3': 456, 'l4': {'l4-1': {'l4-1-1': ["aa", "bb"]}}})

        print(json.dumps(data, indent=4))







if __name__ == '__main__':
    unittest.main()