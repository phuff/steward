(ns steward.core
  (:use [steward.util.epub :as epub]
        [clojure.java.shell :only [sh]]
        [clojure.java.io :as io]
        [clj-time.format :as clj-time-format]
        [clj-time.local :as clj-time-local]
        [clj-config.core :as clj-config])
  (:require [clj-time.core :as clj-time])
  (:gen-class))
(import 'org.apache.commons.mail.MultiPartEmail)
(import 'org.apache.commons.mail.EmailAttachment)

(defn get-epub-item-from-service [service]
  (require (symbol (:libspec service)))
  (let [uuid (str (java.util.UUID/randomUUID))
        id (format "%s-%s" @(ns-resolve *ns* (symbol (:libspec service) "short-name")) uuid)]
    (assoc (@(ns-resolve *ns* (symbol (:libspec service) "get-epub-item")) (:config service))
      :id id :filename (format "%s.html" id))))

(defn generate-output [config]
  (let [volumeNumber (clj-time-format/unparse (clj-time-format/formatter-local "MMddYYYYHHmmssSSS") (clj-time-local/local-now))
        outputPath (str (:outputPath config) volumeNumber)
        items (map get-epub-item-from-service (:services config))]
    (.mkdirs (io/file outputPath))
    (epub/output-epub outputPath
                      (format "Steward Volume %s" volumeNumber)
                      (format "Published On %s" (clj-time-format/unparse (clj-time-format/formatter-local "MMMM dd, YYYY") (clj-time-local/local-now)))
                      "Steward"
                      (format "stewardVolume%s" volumeNumber)
                      items)
    (sh "kindlegen" (format "%s/stewardVolume%s.epub" outputPath volumeNumber))
    (let [attachment (EmailAttachment.)
          email (MultiPartEmail.)]
      (.setPath attachment (format "%s/stewardVolume%s.mobi" outputPath volumeNumber))
      (.setDisposition attachment EmailAttachment/ATTACHMENT)
      (.setDescription attachment "Steward Attachment")
      (.setName attachment (format "stewardVolume%s.mobi" outputPath volumeNumber))
      (.setHostName email (:smtp-host config))
      (.setSslSmtpPort email (:smtp-port config))
      (.setSSL email true)
      (.addTo email (:kindle-email config))
      (.setFrom email (:from-email config) (:from-name config))
      (.attach email attachment)
      (.setAuthentication email (:smtp-username config) (:smtp-password config))
      (.send email)
      )
    )
  nil
  )





(defn initialize-service [service]
  (require (symbol (:libspec service)))
  (@(ns-resolve *ns* (symbol (:libspec service) "initialize-service")) (:config service)))

(defn collect-data-from-service [service]
  (require (symbol (:libspec service)))
  (@(ns-resolve *ns* (symbol (:libspec service) "collect-data")) (:config service)))

(defn initialize-services [config]
  (doseq [service (:services config)]
    (initialize-service service)
  ))

(defn collect-data-from-services [config]
  (doseq [service (:services config)]
    (println "Collecting data")
    (collect-data-from-service service)
    )
  )

;; Parse command line args and run init on modules in config.
;; Factor out epub generation into it's own thing
;; Make it so that we can generate data for a service also
(defn -main
  "Main function"
  [command]
  (let [config (clj-config/read-config "steward-config.clj")]
    (cond (= "output" command) (generate-output config)
          (= "initialize" command) (initialize-services config)
          (= "collect" command) (collect-data-from-services config)
          :else (generate-output config)))
  ; System/exit or else it hangs around for ever.
  (System/exit 0)
  )
