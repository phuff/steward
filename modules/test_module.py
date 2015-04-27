import base
class InputModule(base.InputModule):
    def input(self, steward):
        self.hasRun = True

    def setup(self, steward):
        self.hasConfig = True

class OutputModule(base.OutputModule):
    def outputEpubDoc(self, steward, chapters):
        self.hasRun = True

    def setup(self, steward):
        self.hasConfig = True
