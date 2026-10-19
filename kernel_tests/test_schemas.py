import unittest
from devcircuit.validator import check_schemas
class SchemaTest(unittest.TestCase):
    def test_all_normative_schemas_are_valid(self):self.assertEqual(check_schemas(),[])
if __name__=='__main__':unittest.main()
