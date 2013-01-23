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

(defn getEpubItemFromService [service]
  (require (symbol (:libspec service)))
  (let [uuid (str (java.util.UUID/randomUUID))
        id (format "%s-%s" @(ns-resolve *ns* (symbol (:libspec service) "short-name")) uuid)]
    (assoc (@(ns-resolve *ns* (symbol (:libspec service) "get-epub-item")) (:config service))
      :id id :filename (format "%s.html" id))))

(defn -main
  "Main function"
  [& args]
  (let [config (clj-config/read-config "steward-config.clj")
        volumeNumber (clj-time-format/unparse (clj-time-format/formatter-local "MMddYYYYHHmmssSSS") (clj-time-local/local-now))
        outputPath (str (:outputPath config) volumeNumber)
        items (map getEpubItemFromService (:services config))]
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
