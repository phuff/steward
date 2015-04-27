class BaseModule:
    def __init__(self, config):
        self.config = config

class InputModule(BaseModule):
    def input(self, steward):
        pass

class OutputModule(BaseModule):
    def __init__(self, config):
        self.config = config

    # Modifies chapters, appending a chapter to the end
    def outputEpubDoc(self, steward, chapters):
        pass
