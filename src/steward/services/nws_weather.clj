(ns steward.services.nws-weather
    (:use [clojure.data.zip.xml]
          [clj-time.format :as clj-time-format]
          [clj-time.coerce :as clj-time-coerce]
          [datomic.api :only [q db] :as d])
    (:require [clojure.xml :as xml]
              [clojure.zip :as zip]
              [clj-time.core :as clj-time]
              )
    (:gen-class))

(def short-name "nws-weather")

(def weather-temp-formatter (clj-time-format/formatters :date-time-no-ms))

(defn getPeriodNamesForLayoutKeys [zipped layout-keys]
  (map (fn [layout-key] (map (fn [period-name timestamp] {:period-name period-name :timestamp (clj-time-format/parse weather-temp-formatter timestamp)})
                             (xml-> zipped :data (attr= :type "forecast") :time-layout [:layout-key layout-key] :start-valid-time (attr :period-name))
                             (xml-> zipped :data (attr= :type "forecast") :time-layout [:layout-key layout-key] :start-valid-time text)))
       layout-keys))

(defn getTimeLayoutMap [zipped]
  (let [layout-keys (xml-> zipped :data (attr= :type "forecast") :time-layout :layout-key text)]
    (zipmap layout-keys (getPeriodNamesForLayoutKeys zipped layout-keys))))

(defn getWeather [zipped timeLayouts]
  (let [timeLayout (first (xml-> zipped :data (attr= :type "forecast") :parameters :weather (attr :time-layout)))
        weather (xml-> zipped :data (attr= :type "forecast") :parameters :weather :weather-conditions (attr :weather-summary))]
    (map (fn [date forecast] {:date date :forecast forecast}) (get timeLayouts timeLayout) weather)))

(defn getTemps [zipped timeLayouts typeString]
  (let [timeLayout (first (xml-> zipped :data (attr= :type "forecast") :parameters :temperature (attr= :type typeString) (attr :time-layout)))
        temps (xml-> zipped :data (attr= :type "forecast") :parameters :temperature (attr= :type typeString) :value text)]
    (zipmap (get timeLayouts timeLayout) (map (fn [temp] {:temp temp :type typeString}) temps))))

(defn getMaxTemps [zipped timeLayouts]
  (getTemps zipped timeLayouts "maximum"))

(defn getMinTemps [zipped timeLayouts]
  (getTemps zipped timeLayouts "minimum"))

(defn compareObservationTimestamps [item1 item2]
  (if (clj-time/before? (:timestamp (:date item1)) (:timestamp (:date item2)))
    true
    false))

(defn storeTempInDb [connection config temp]
  (let [result (q '[:find ?e
                    :in $ ?name ?lat ?lon ?date
                    :where
                    [?e :temperature/location-name ?name]
                    [?e :temperature/location-lat ?lat ]
                    [?e :temperature/location-lon ?lon]
                    [?e :temperature/timestamp ?date]]
                  (db connection)
                  (:location-name config)
                  (:latitude config)
                  (:longitude config)
                  (to-date (:timestamp (key temp)))
                  )
        tempId (if (> (count result) 0) (ffirst result) (d/tempid :db.part/user))]
    (println (format "Temp: %s Type: %s Date: %s" (:type (val temp)) (:temp (val temp)) (to-date (:timestamp (key temp)))))
    @(d/transact connection [{:db/id tempId :temperature/location-name (:location-name config)
                              :temperature/location-lat (:latitude config)
                              :temperature/location-lon (:longitude config)
                              :temperature/value (double (read-string (:temp (val temp))))
                              :temperature/type (if (= (:type (val temp) "maximum")) :temperature.type/max :temperature.type/min)
                              :temperature/timestamp (to-date (:timestamp (key temp)))
                              :temperature/period-name (:period-name (key temp))}])
    )
  )

(defn storeWeatherInDb [config]
  (let [zipped (zip/xml-zip (xml/parse (format "http://forecast.weather.gov/MapClick.php?lat=%s&lon=%s&unit=0&lg=english&FcstType=dwml" (:latitude config) (:longitude config))))
        timeLayouts (getTimeLayoutMap zipped)
        maxTemps (getMaxTemps zipped timeLayouts)
        minTemps (getMinTemps zipped timeLayouts)
        weather  (getWeather zipped timeLayouts)]
    (println "About to create database")
    (d/create-database (:datomic-url config))
    (println "About to connect to db")
    (let [conn (d/connect (:datomic-url config))]
      (println "Nws Weather about to put maxTemps in db")
      (doseq [temp maxTemps]
        (storeTempInDb conn config temp)
        )
      (println "Nws Weather about to put minTemps in db")
      (doseq [temp minTemps]
        (storeTempInDb conn config temp)
        )
      )))
;; Refactor this function into two parts: one of them stores things in datomic
;; The other fetches them from datomic
(defn getForecastMap [latitude longitude]
  (let [zipped (zip/xml-zip (xml/parse (format "http://forecast.weather.gov/MapClick.php?lat=%s&lon=%s&unit=0&lg=english&FcstType=dwml" latitude longitude)))
        timeLayouts (getTimeLayoutMap zipped)
        maxTemps (getMaxTemps zipped timeLayouts)
        minTemps (getMinTemps zipped timeLayouts)
        weather  (getWeather zipped timeLayouts)]

    {:temps (merge maxTemps minTemps)
     :weather weather}
    )
  )


(defn translateTempType [typeString]
  (if (= typeString "maximum")
    "High"
    (if (= typeString "minimum")
      "Low"
      ""))
  )

(defn printForecast [forecastMap]
  (let [temps (:temps forecastMap)
        weather (:weather forecastMap)]
    (doseq [item weather]
      (print (:period-name (:date item)) "\n")
      (print (str "\t" (:forecast item)) "\n")
      (print (str "\t" (translateTempType (:type (get temps (:date item)))) ": " (:temp (get temps (:date item)))) "\n")
    )))

(defn getTableHeader [forecastMap]
  (str "<tr>" (apply str (map (fn [item] (str "<th>" (:period-name (:date item)) "</th>")) (:weather forecastMap))) "</tr>"))

(defn getTableForecastRows [forecastMap]
  (let [temps (:temps forecastMap)]
    (apply str (map (fn [item] (str "<tr><td>" (:period-name (:date item)) "</td>"
                                                "<td>" (:forecast item) "</td>"
                                                "<td>" (translateTempType (:type (get temps (:date item)))) ": " (:temp (get temps (:date item))) "</td></tr>"))
                                  (:weather forecastMap)))))

(defn getTableTempRow [forecastMap]
  (let [temps (:temps forecastMap)]
    (str "<tr>" (apply str (map (fn [item] (str "<td>" (translateTempType (:type (get temps (:date item)))) ": " (:temp (get temps (:date item))) "</td>")) (:weather forecastMap))) "</tr>")))

(defn generateDocumentFromMap [forecastMap locationName]
  (str (format "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>
<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.1//EN\" \"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd\">
<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\">
  <head>
    <meta http-equiv=\"Content-Type\" content=\"application/xhtml+xml; charset=utf-8\" />
    <title>Weather Forecast for %s</title>
</head>
  <body><h1>Weather for %s</h1><table>" locationName locationName)
       (getTableForecastRows forecastMap)
       "</table></body>
</html>"))

(defn get-epub-item [config]
  {:title (format "Weather for %s" (:location-name config)) :content (generateDocumentFromMap (getForecastMap (:latitude config) (:longitude config)) (:weatherLocationName config))})


(defn initialize-service [config]
  (d/create-database (:datomic-url config))
  (let [conn (d/connect (:datomic-url config))
        schema-tx (read-string (slurp "src/steward/services/nws_weather.dtm"))]
    @(d/transact conn schema-tx))
  )

(defn collect-data [config]
  (println "Nws Weather about to storeWeatherInDb")
  (storeWeatherInDb config)
  )