import unittest
from nlptime import nlptime
import logging
import datetime

logging.basicConfig(filename="nlptime_tests.log", level=logging.DEBUG, filemode="w")

nlp_model = nlptime()

class MainTests(unittest.TestCase):
    def test_hours_02(self):
        hour_tests = [
            "in 2 hours",
            "in an hour",
            "at 1:00",
            "3 am"
        ]
        for test in hour_tests:
            print (test)
            response = nlp_model.parse(test)
            print (response)
            self.assertIsInstance(response, datetime.datetime)
    def test_loading_01(self):
        #Attributes that have to be in the main class
        required_attributes = [
            "parser",
            "time_words",
            "lang_utils",
            "model",
            "lst_offset",
            "preference",
            'return_delta',
            "allow_none"
        ]
        for attr in required_attributes:
            self.assertTrue(attr in nlp_model.__dict__.keys())


if __name__ == '__main__':
    unittest.main()
