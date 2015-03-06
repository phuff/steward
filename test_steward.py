import unittest
from steward import Steward

class StewardTest(unittest.TestCase):

    def test_run(self):
        steward = Steward()
        steward.run()
        self.assertEqual(True, True)

    def test_config(self):
        steward = Steward({'hello': 1, 'there': 42})
        self.assertEqual(steward.getConfig('hello'), 1)
        self.assertEqual(steward.getConfig('there'), 42)

if __name__ == '__main__':
    unittest.main()
