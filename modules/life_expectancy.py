import base
from datetime import datetime
import dateutil.parser
from dateutil.relativedelta import relativedelta

class InputModule(base.InputModule):
    def setup(self, steward):
        pass

class OutputModule(base.OutputModule):
    def setup(self, steward):
        pass
    def outputEpubDoc(self, steward, chapters):
        birthdate = dateutil.parser.parse(self.config['date_of_birth'])
        life_expectancy = self.config['life_expectancy']
        output = u'''Days left before estimated death: {0}<br />
<hr style="width: 100%" />
Years left: {1}<br />
'''.format(((birthdate + relativedelta(years=+int(float(life_expectancy)))) - datetime.now()).days,
        ((birthdate + relativedelta(years=+int(float(life_expectancy))))- datetime.now()).days / 365)
        chapters.append({'title': u'Life Expectancy', 'body': output})
