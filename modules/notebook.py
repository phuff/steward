import base
from datetime import datetime, date
import dateutil.parser
from dateutil.relativedelta import relativedelta

class InputModule(base.InputModule):
    def setup(self, steward):
        pass

def calculateAge(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

class OutputModule(base.OutputModule):
    def setup(self, steward):
        pass
    def outputEpubDoc(self, steward, chapters):
        chapters.append({'title': self.config['title'], 'body': self.config['contents']})
