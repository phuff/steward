#!/usr/bin/env python
import json

class Steward:
    def __init__(self, config = {}):
        self.config = config
        pass

    def getConfig(self, key):
        if self.config.has_key(key):
            return self.config[key]

    def run(self):
        print "config: %s\n" % (self.config, )
        pass


if __name__ == '__main__':
    f = open("config.json")
    config = json.load(f)
    s = Steward(config)
    s.run()
