import base
from datetime import datetime
from sqlalchemy import *
from lxml import etree
import re, dateutil.parser, urllib2
metadata = MetaData()

weather_table = Table("weather", metadata,
                      Column('id', Integer, primary_key=True),
                      Column('lat', Float),
                      Column('lon', Float),
                      Column('place_name', String(100, convert_unicode=True)),
                      Column('forecast_temp', Integer),
                      Column('temperature_type', String(5, convert_unicode=True)),
                      Column('forecast_text', String(512, convert_unicode=True)),
                      Column('forecast_time_text', String(100, convert_unicode=True)),
                      Column('forecast_date', DateTime),
                      Column('forecast_obtained', DateTime, default=datetime.now))

weather_index = Index('weather_idx',
                      weather_table.c.forecast_date,
                      weather_table.c.forecast_obtained)

class InputModule(base.InputModule):
    def setup(self, steward):
        engine = steward.getDbEngine()
        weather_table.create(bind=engine, checkfirst=True)

    def input(self, steward):
        #url = "http://localhost:5000/weather?lat=%s&lon=%s"
        url = "http://forecast.weather.gov/MapClick.php?lat=%s&lon=%s&unit=0&lg=english&FcstType=dwml"
        #lat=40.5955
        #lon=-111.961
        engine = steward.getDbEngine()
        #print "Opening: {}".format(url % (self.config['lat'], self.config['lon']))
        try:
            forecastXml = etree.parse(urllib2.urlopen(url % (self.config['lat'], self.config['lon'])))
        except:
            return
        self.parseTimeLayouts(forecastXml)
        forecasts = {}

        for temperature in forecastXml.xpath("//temperature"):
            temperatureType = ""
            if temperature.get("type") == "minimum":
                temperatureType = "low"
            elif temperature.get("type") == "maximum":
                temperatureType = "high"
            else: # we don't know what temperature type it is, so just skip this one
                continue
            for i in xrange(1, len(temperature)):
                forecasts[self.timeLayouts[temperature.get("time-layout")][i - 1]] = {"place_name": self.config["place_name"],
                                                                                      "lat": self.config["lat"],
                                                                                      "lon": self.config["lon"],
                                                                                      "temperature_type": temperatureType,
                                                                                      "forecast_temp": temperature[i].text}
        for wordedForecast in forecastXml.xpath("//wordedForecast"):
            timeLayoutName = wordedForecast.get("time-layout")
            timeLayout = self.timeLayouts[timeLayoutName]
            texts = wordedForecast.xpath("//text")
            for i in xrange(0, len(texts)):
                if timeLayout[i] in forecasts:
                    forecasts[timeLayout[i]]["forecast_text"] = texts[i].text

        for key, forecast in forecasts.iteritems():
            engine.execute(weather_table.insert(), lat=forecast["lat"], lon=forecast["lon"],
                           place_name=forecast["place_name"], forecast_temp=forecast["forecast_temp"],
                           temperature_type=forecast["temperature_type"], forecast_text=forecast["forecast_text"],
                           forecast_time_text=key[1], forecast_date=self.dateTimeFromString(key[0]))


    def parseTimeLayouts(self, forecastXml):
        self.timeLayouts = {}
        for timeLayout in forecastXml.xpath("//time-layout"):
            self.timeLayouts[timeLayout[0].text] = [(timeLayout[i].text, timeLayout[i].get("period-name")) for i in xrange(1, len(timeLayout))]


    def dateTimeFromString(self, tzString):
        return dateutil.parser.parse(tzString)

class OutputModule(base.OutputModule):
    def setup(self, steward):
        self.engine = steward.getDbEngine()

    def outputEpubDoc(self, steward, chapters):
        weather_alias = weather_table.alias()
        from_obj = weather_table.outerjoin(weather_alias, and_(weather_table.c.place_name==weather_alias.c.place_name, weather_table.c.forecast_date==weather_alias.c.forecast_date, weather_table.c.forecast_obtained < weather_alias.c.forecast_obtained))
        query = weather_table.select()
        query = query.select_from(from_obj)
        query = query.where(weather_alias.c.id == None)
        query = query.where(weather_table.c.lat==self.config["lat"])
        query = query.where(weather_table.c.lon==self.config["lon"])
        query = query.where(weather_table.c.forecast_date >= datetime.now())
        query = query.order_by(asc(weather_table.c.forecast_date))
        results = self.engine.execute(query)
        forecastPlace = self.config["place_name"]
        first = True
        header = ""#<tr><th></th><th>Temp</th><th>Forecast</th></tr>"
        rows = ""
        i = 0
        forecasts = []
        for forecast in results:
            forecasts.append(forecast)
        for forecast in forecasts:
            i += 1
            borderStyle = 'border-bottom: 1px solid black;' if i < len(forecasts) else ''
            rows += "<tr>"
            tempTypeText = "High: " if forecast.temperature_type == "high" else "Low: "
            rows += "<td style='{0} padding-top: 10px; padding-bottom: 10px; font-size: x-small; width: 35%;'>".format(borderStyle) + forecast.forecast_time_text + "<br />" +  tempTypeText + str(forecast.forecast_temp) + "</td>"
            rows += "<td style='{0} paddint-top: 10px; padding-bottom: 5px; font-size: x-small; width: 65%;'>".format(borderStyle) + forecast.forecast_text + "</td>"
            rows += "</tr>\n"

        chapters.append({'title': "Weather for %s" % (forecastPlace, ),
                         'body': "<h1>Weather for %s</h1><br /><table style='border-collapse: collapse;'>\n" % (forecastPlace, ) + header + "\n" + rows + "</table>\n"})
