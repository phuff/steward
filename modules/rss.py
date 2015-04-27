import base
from datetime import datetime
from sqlalchemy import *
import re, dateutil.parser, urllib2, hashlib
import feedparser
from HTMLParser import HTMLParser

#Tag stripper from http://stackoverflow.com/questions/753052/strip-html-from-strings-in-python

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.result = []
    def handle_data(self, d):
        self.fed.append(d)
    def handle_charref(self, number):
        codepoint = int(number[1:], 16) if number[0] in (u'x', u'X') else int(number)
        self.result.append(unichr(codepoint))

    def handle_entityref(self, name):
        codepoint = htmlentitydefs.name2codepoint[name]
        self.result.append(unichr(codepoint))
    def get_text(self):
        return u''.join(self.result)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_text()

metadata = MetaData()

rss_table = Table("rss", metadata,
                  Column('id', String(512, convert_unicode=True), primary_key=True),
                  Column('title', String(512, convert_unicode=True)),
                  Column('description', String(512, convert_unicode=True)),
                  Column('link', String(512, convert_unicode=True)),
                  Column('feed_title', String(512, convert_unicode=True)),
                  Column('feed_url', String(512, convert_unicode=True)),
                  Column('date_retrieved', DateTime, default=datetime.now),
                  Column('section_id', String(512, convert_unicode=True)))

rss_last_output_table = Table("rss_last_output", metadata,
                              Column('id', String(512, convert_unicode=True)),
                              Column('last_output', DateTime))

rss_index = Index('rss_idx',
                  rss_table.c.id,
                  rss_table.c.title,
                  rss_table.c.description,
                  rss_table.c.feed_url)

class InputModule(base.InputModule):
    def setup(self, steward):
        engine = steward.getDbEngine()
        rss_table.create(bind=engine, checkfirst=True)
        rss_last_output_table.create(bind=engine, checkfirst=True)

    def input(self, steward):
        engine = steward.getDbEngine()

        for feedUrl in self.config["feeds"]:
            feed = feedparser.parse(feedUrl)
            for entry in feed.entries:
                id = ""
                if hasattr(entry, "id"):
                    id = entry.id
                else:
                    id = hashlib.sha1(entry.title + entry.description + entry.link).hexdigest()
                query = rss_table.select()
                query = query.where(rss_table.c.id==id)
                result = engine.execute(query)
                if len(result.fetchall()) == 0:
                    engine.execute(rss_table.insert(), id=id, title=entry.title,
                                   description=entry.description, link=entry.link,
                                   feed_title=feed.feed.title, feed_url=feedUrl,
                                   section_id=self.config['id'])

class OutputModule(base.OutputModule):
    def setup(self, steward):
        pass

    def outputEpubDoc(self, steward, chapters):
        engine = steward.getDbEngine()
        query = rss_last_output_table.select()
        query = query.where(rss_last_output_table.c.id == self.config['id'])
        results = engine.execute(query)
        last_output = datetime.min
        for result in results:
            last_output = result.last_output
        if last_output == datetime.min:
            engine.execute(rss_last_output_table.insert(), id=self.config['id'], last_output=datetime.now())
        else:
            updateQuery = rss_last_output_table.update().where(rss_last_output_table.c.id==self.config['id']).values(last_output=datetime.now())
            engine.execute(updateQuery)

        # todo: loop over feeds here and output each one as a chapter
        query = rss_table.select()
        query = query.where(rss_table.c.date_retrieved > last_output)
        query = query.where(rss_table.c.section_id == self.config['id'])
        query = query.order_by(asc(rss_table.c.date_retrieved))
        results = engine.execute(query)
        output = u""
        entries = []
        for entry in results:
            entries.append(entry)
        i = 0
        for entry in entries:
            i += 1
            border = u"<hr style='width: 100%;' />" if i < len(entries) else u""

            output += u"<span style='font-size: small; font-style: italic;'>{0}</span><br /><span style='font-size: small; font-weight: bold;>{1}</span><br/><span style='font-size: small'>{2}</span>{3}".format(entry.feed_title, entry.title, strip_tags(entry.description), border)
        chapters.append({'title': "RSS Feeds", 'body': output})
