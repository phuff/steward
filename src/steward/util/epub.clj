(ns steward.util.epub
  (:use [clojure.data.zip.xml]
        [clj-time.format :as clj-time-format])
  (:require [clojure.xml :as xml]
            [clojure.zip :as zip]
            [clj-time.core :as clj-time])
  (:gen-class))

(import java.util.zip.ZipEntry)
(import java.util.zip.ZipOutputStream)
(import javax.imageio.ImageIO)
(import java.awt.image.BufferedImage)
(import java.awt.Color)

(defn writeZipStringOutput [zip-output filename content]
  (let [contentBytes (.getBytes content "UTF-8")]
    (.putNextEntry zip-output (new ZipEntry filename))
    (.write zip-output contentBytes 0 (alength contentBytes))))

(defn writeImageJpgOutput [zip-output filename image]
  (.putNextEntry zip-output (new ZipEntry filename))
  (ImageIO/write image "jpeg" zip-output))

(defn writeMimeType [zip-output]
  (writeZipStringOutput zip-output "mimetype" "application/epub+zip")
  )

(defn getManifestItem [item]
  (format "<item id=\"%s\" href=\"%s\" media-type=\"application/xhtml+xml\" />\n" (:id item) (:filename item)))

(defn getSpineItem [item]
  (format "<itemref idref=\"%s\" />\n" (:id item)))

(defn getOpfFileText [title author bookfilename documents]
  (str (format "<?xml version=\"1.0\"?>
<package version=\"2.0\" xmlns=\"http://www.idpf.org/2007/opf\">

  <metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\" xmlns:opf=\"http://www.idpf.org/2007/opf\">
    <dc:title>%s</dc:title>
    <dc:language>en</dc:language>
    <dc:creator opf:file-as=\"%s\" opf:role=\"aut\">%s</dc:creator>
  </metadata>

  <manifest>\n" title author author)
;;       (getManifestItem {:id "cover" :filename "cover.jpg"})
       (apply str (map getManifestItem documents))
       (getManifestItem {:id "ncx" :filename (format "%s.ncx" bookfilename)})
       "</manifest>\n"
       "<spine toc=\"ncx\">\n"
       (apply str (map getManifestItem documents))
       "</spine>\n"
       "</package>\n"
       ))

(defn writeOpfFile [zip-output title author bookfilename documents]
  (writeZipStringOutput zip-output
                  (str bookfilename ".opf")
                  (getOpfFileText title author bookfilename documents)))

(defn getNavPointForItem [playorder item]
  (format "<navPoint class=\"chapter\" id=\"%s\" playorder=\"%s\">
  <navLabel><text>%s</text></navLabel>
  <content src=\"%s\" />
  </navPoint>\n" (:id item) playorder (:title item) (:filename item)))

(defn getNcxFileText [title author bookfilename documents]
  (str (format "<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE ncx PUBLIC \"-//NISO//DTD ncx 2005-1//EN\"
\"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd\">

<ncx version=\"2005-1\" xml:lang=\"en\" xmlns=\"http://www.daisy.org/z3986/2005/ncx/\">

  <head>
<!-- The following four metadata items are required for all NCX documents,
including those conforming to the relaxed constraints of OPS 2.0 -->

    <meta name=\"dtb:uid\" content=\"123456789X\"/> <!-- same as in .opf -->
    <meta name=\"dtb:depth\" content=\"1\"/> <!-- 1 or higher -->
    <meta name=\"dtb:totalPageCount\" content=\"0\"/> <!-- must be 0 -->
    <meta name=\"dtb:maxPageNumber\" content=\"0\"/> <!-- must be 0 -->
  </head>
  <docTitle>
    <text>%s</text>
  </docTitle>

  <docAuthor>
    <text>%s</text>
  </docAuthor>
  <navMap>" title author)
       (apply str (map-indexed (fn [idx item] (getNavPointForItem idx item)) documents))
       "</navMap>
</ncx>"))


(defn writeNcxFile [zip-output title author bookfilename documents]
  (writeZipStringOutput zip-output
                  (str bookfilename ".ncx")
                  (getNcxFileText title author bookfilename documents)))

(defn writeDocumentFile [zip-output document]
  (writeZipStringOutput zip-output
                  (str (:filename document))
                  (:content document))
  )


(defn writeCoverImage [zip-output title subtitle author]
  (let [height 1000 ;; From https://kdp.amazon.com/self-publishing/help?topicId=A2J0TRG6OPX0VM
        width 625
        bi (BufferedImage. width height BufferedImage/TYPE_INT_ARGB)
        g (.createGraphics bi)]
    (.setColor g Color/white)
    (.fillRect g 0 0 width height)
    (.setColor g Color/black)
    (.drawString g title 100 100)
    (.drawString g subtitle 100 200)
    (.drawString g author 100 300)
    (writeImageJpgOutput zip-output "cover.jpg" bi)
    )
  )

(defn output-epub [basepath title subtitle author bookfilename documents]
  (with-open [zip-output (ZipOutputStream. (clojure.java.io/output-stream (str basepath (System/getProperty "file.separator") bookfilename ".epub")))]
    ;;(writeCoverImage zip-output title subtitle author)
    (writeMimeType zip-output)
    (writeOpfFile zip-output title author bookfilename documents)
    (writeNcxFile zip-output title author bookfilename documents)
    (doseq [document documents]
      (writeDocumentFile zip-output document))
    ))