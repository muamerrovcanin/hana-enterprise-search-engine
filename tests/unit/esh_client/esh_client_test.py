import unittest
import json

import esh_client


class TestStringMethods(unittest.TestCase):

    
    def test_esh_configuration_element(self):
        esh_configuration_element_json = '''
            {
                "ref": ["level0", "level1"],
                "@Search": {
                    "defaultSearchElement": true
                }
            }
        '''
        esh_configuration_element = esh_client.EshConfigurationElement.parse_obj(json.loads(esh_configuration_element_json))
        print(json.dumps(esh_configuration_element.dict(exclude_none=True,by_alias=True)))
        self.assertEqual(esh_configuration_element.dict(exclude_none=True,by_alias=True), {"ref": ["level0", "level1"], "@Search": { "defaultSearchElement": True}})
        
        #term_json = '''
        #    {
        #        "type": "StringValue",
        #        "value": "Heidelberg"
        #    }
        #'''
        # term_dict = json.loads(term_json)
        # term2 = esh_client.StringValue.parse_obj(term_dict)
        # self.assertEqual(term2.dict(exclude_none=True), term_dict)

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