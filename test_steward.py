import unittest, os.path
from steward import Steward
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

Base = declarative_base()
class TestModel(Base):
    __tablename__ = 'test_model'
    id = Column(Integer, primary_key=True)

class StewardTest(unittest.TestCase):

    def test_run(self):
        steward = Steward()
        steward.run()
        self.assertEqual(True, True)

    def test_config(self):
        steward = Steward({'hello': 1, 'there': 42})
        self.assertEqual(steward.getConfig('hello'), 1)
        self.assertEqual(steward.getConfig('there'), 42)

    def test_get_engine(self):
        steward = Steward({'db_url': 'sqlite:////tmp/steward.db'})
        engine = steward.getDbEngine()
        Base.metadata.create_all(engine)
        self.assertTrue(os.path.isfile('/tmp/steward.db'))
        os.unlink('/tmp/steward.db')

    def test_load_module(self):
        steward = Steward({'epubOutput': True,
                           'modules': {'input': [{'name': 'test_module'}],
                                       'output': [{'name': 'test_module'}]}})
        steward.run()
        self.assertTrue(steward.getModule('input','test_module')[0].hasConfig)
        self.assertTrue(steward.getModule('output','test_module')[0].hasConfig)
        self.assertTrue(steward.getModule('input','test_module')[0].hasRun)
        self.assertTrue(steward.getModule('output','test_module')[0].hasRun)


    def test_setup_module(self):
        steward = Steward({'modules': {'input': [{'name': 'test_module'}],
                                       'output': [{'name': 'test_module'}]}})
        steward.setupModules()
        self.assertTrue(steward.getModule('input','test_module')[0].hasConfig)
        self.assertTrue(steward.getModule('output','test_module')[0].hasConfig)

    def test_weather_module(self):
        steward = Steward({'db_url': 'sqlite://',
                           'modules': {'input': [{'name': 'weather',
                                                  'place_name': 'West Jordan',
                                                  'lat': '40.5955',
                                                  'lon': '-111.961'}]}})
        steward.run()
        engine = steward.getDbEngine()
        result = engine.execute("select * from weather order by forecast_date ASC")
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
