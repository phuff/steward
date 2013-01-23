(defproject steward "0.1.0-SNAPSHOT"
  :description "Steward"
  :url "http://example.com/FIXME"
  :license {:name "Apache Public License"
            :url "http://www.apache.org/licenses/LICENSE-2.0.html"}
  :dependencies [[org.clojure/clojure "1.4.0"]
                 [org.clojure/data.zip "0.1.1"]
                 [clj-time "0.4.4"]
                 [clj-config "0.2.0"]
                 [org.apache.commons/commons-email "1.2"]]
  :repositories [["central-proxy" "http://repository.sonatype.org/content/repositories/central/"]]
  :main steward.core)
