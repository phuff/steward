#!/usr/bin/env python
import json, os.path, datetime, StringIO, smtplib
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders
import sqlalchemy
from epub_builder import EpubBuilder
from subprocess import call

class Steward:
    def __init__(self, config = {}):
        self.config = config
        self.engine = None
        pass

    def getConfig(self, key):
        if self.config.has_key(key):
            return self.config[key]
        return None

    def setupModules(self):
        self.loadModules()
        for key, modules in self.modules['input'].iteritems():
            for module in modules:
                module.setup(self)
        for section in self.modules['output']:
            for module in section['modules']:
                module.setup(self)


    def run(self):
        self.loadModules()
        self.setupModules()
        for key, modules in self.modules['input'].iteritems():
            for module in modules:
                module.input(self)
        if self.getConfig('kindleOutput') or self.getConfig('epubOutput'):
            epubSections = []

            for section in self.modules['output']:
                epubSection = {'title': section['section-title'],
                               'chapters': []}
                for module in section['modules']:
                    module.outputEpubDoc(self, epubSection['chapters'])
                epubSections.append(epubSection)

        if self.getConfig('kindleOutput') or self.getConfig('epubOutput'):
            today = datetime.date.today().strftime("%Y-%m-%d")
            epubFilename = "/tmp/steward-%s.epub" % (today, )
            mobiFilename = "/tmp/steward-%s.mobi" % (today, )
            eb = EpubBuilder(epubFilename, "Steward for %s" % (datetime.date.today().strftime("%B %d, %Y")), "Information Steward", epubSections, True)
            eb.writeBookFile()
            if self.getConfig('kindleOutput'):
                call(["/home/phuff/bin/kindlegen", epubFilename])

                message = MIMEMultipart()
                message["Subject"] = ""
                message['To']  = self.getConfig('kindleEmailAddress')
                message['From'] = self.getConfig('senderEmailAddress')
                fp = open(mobiFilename)
                attachment = MIMEBase("application", "x-mobipocket-ebook")
                attachment.set_payload(fp.read())
                attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(mobiFilename))
                fp.close()
                encoders.encode_base64(attachment)
                message.attach(attachment)
                server = smtplib.SMTP(self.getConfig('senderSMTPHost'))
                server.ehlo()
                server.starttls()
                server.login(self.getConfig('senderEmailAddress'), self.getConfig('senderEmailPassword'))
                server.sendmail(self.getConfig('senderEmailAddress'), self.getConfig('kindleEmailAddress'), message.as_string())
                server.quit()


    def getModule(self, moduleType, moduleName):
        if moduleType in self.modules:
            if moduleName in self.modules[moduleType]:
                return self.modules[moduleType][moduleName]
        return None

    def loadModules(self):
        self.modules = {'input': {}, 'output': []}
        if not self.config.has_key('modules'):
            return
        if 'input' in self.config['modules']:
            for moduleConfig in self.config['modules']['input']:
                module = __import__('modules.%s'  % (moduleConfig['name'], ))
                submodule = getattr(module, moduleConfig['name'])
                if hasattr(submodule, 'InputModule'):
                    kls = getattr(submodule, 'InputModule')
                    if not self.modules['input'].has_key(moduleConfig['name']):
                        self.modules['input'][moduleConfig['name']] = []
                    self.modules['input'][moduleConfig['name']].append(kls(moduleConfig))
        if 'output' in self.config['modules']:
            for section in self.config['modules']['output']:
                loadedSection = {'section-title': section['section-title'],
                           'modules': []}
                for moduleConfig in section['modules']:
                    module = __import__('modules.%s'  % (moduleConfig['name'], ))
                    submodule = getattr(module, moduleConfig['name'])
                    if hasattr(submodule, 'OutputModule'):
                        kls = getattr(submodule, 'OutputModule')
                        loadedSection['modules'].append(kls(moduleConfig))
                self.modules['output'].append(loadedSection)


    def getDbEngine(self):
        if self.engine is None:
            self.engine = sqlalchemy.create_engine(self.getConfig('db_url'))
        return self.engine


if __name__ == '__main__':
    f = open("config.json")
    config = json.load(f)
    s = Steward(config)
    s.run()
