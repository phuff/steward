# epub_builder.py
# Basic epub builder for python.
# Copyright 2015 by Paul Huff

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
import os,re
from zipfile import ZipFile

class OpfFile:
    def __init__(self, title, author, periodical=False):
        self.periodical = periodical
        if self.periodical:
            periodicalString = u'''        <x-metadata>
      <output content-type="application/x-mobipocket-subscription-magazine" encoding="utf-8"/>
    </x-metadata>'''
        else:
            periodicalString = u''

        self.outputString = u'''<?xml version="1.0"?>
<package version="2.0" xmlns="http://www.idpf.org/2007/opf">

  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
      <dc-metadata>
          <dc:title>%s</dc:title>
          <dc:language>en</dc:language>
          <dc:creator opf:file-as="%s" opf:role="aut">%s</dc:creator>
      </dc-metadata>
%s
  </metadata>

  <manifest>
''' % ( title, author, author, periodicalString)

    def writeToEpub(self, chapters, epubFile):
        spineContents = u''
        if self.periodical:
            for section in chapters:
                for chapter in section['chapters']:
                    self.outputString += u'''   <item id="{0}" href="{1}" media-type="application/xhtml+xml" />
'''.format(chapter['id'], chapter['filename'])
                    spineContents += u'   <itemref idref="{0}" />'.format(chapter['id'])
        else:
            for chapter in chapters:
                self.outputString += u'''   <item id="{0}" href="{1}" media-type="application/xhtml+xml" />
'''.format(chapter['id'], chapter['filename'])
                spineContents += u'   <itemref idref="{0}" />'.format(chapter['id'])

        self.outputString += u'''<item id="ncx" href="ncxfile.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>

  <spine toc="ncx">
  {0}
  </spine>
</package>'''.format(spineContents)

        epubFile.writestr('OEBPS/opffile.opf', self.outputString)

class NcxFile:
    def __init__(self, title, author, periodical=False):
        self.periodical = periodical
        self.title = title
        self.outputString = u'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">

<ncx version="2005-1" xml:lang="en" xmlns="http://www.daisy.org/z3986/2005/ncx/">

  <head>
<!-- The following four metadata items are required for all NCX documents,
including those conforming to the relaxed constraints of OPS 2.0 -->

    <meta name="dtb:uid" content="123456789X"/> <!-- same as in .opf -->
    <meta name="dtb:depth" content="1"/> <!-- 1 or higher -->
    <meta name="dtb:totalPageCount" content="0"/> <!-- must be 0 -->
    <meta name="dtb:maxPageNumber" content="0"/> <!-- must be 0 -->
  </head>
  <docTitle>
    <text>%s</text>
  </docTitle>

  <docAuthor>
    <text>%s</text>
  </docAuthor>
  <navMap>
''' % (title, author)

    def writeToEpub(self, chapters, zipFile):
        chapterNumber = 1
        if self.periodical:
            first = True
            playorder = 1
            for section in chapters:
                if first:
                    self.outputString += u'''    <navPoint playorder="0" class="periodical" id="periodical">
        <navLabel><text>{0}</text></navLabel>
            <content src="{1}" />
'''.format(self.title, section['chapters'][0]["filename"])
                    first = False

                self.outputString += u'''                <navPoint playorder="{0}" class="section" id="section-{0}">
                <navLabel><text>{1}</text></navLabel>
                <content src="{2}" />
'''.format(playorder, section['title'], section['chapters'][0]["filename"])
                playorder += 1
                for j, chapter in enumerate(section['chapters']):
                    self.outputString += u'''                    <navPoint playorder="{0}" class="article" id="{1}">
                        <navLabel><text>{2}</text></navLabel>
                        <content src="{3}" />
                    </navPoint>
'''.format(playorder, chapter['id'], chapter['title'], chapter['filename'])
                    playorder += 1
                self.outputString += u'                </navPoint>\n'
            self.outputString += u'    </navPoint>\n'
        else:
            for chapter in chapters:
                self.outputString += u'''   <navPoint class="chapter" id="%s" playorder="%s">
      <navLabel><text>%s</text></navLabel>
      <content src="%s" />
   </navPoint>
''' % (chapter['id'], chapterNumber, chapter['title'], chapter['filename'])
                chapterNumber += 1

        self.outputString += u'''   </navMap>
</ncx>'''
        zipFile.writestr("OEBPS/ncxfile.ncx", self.outputString)

class ContainerFile:
    def __init__(self):
        self.outputString = u'''<?xml version="1.0" encoding="UTF-8" ?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="%s" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>''' % ('OEBPS/opffile.opf')

    def finish(self, zipFile):
        zipFile.writestr('OEBPS/META-INF/container.xml', self.outputString)

class EpubBuilder:
    def __init__(self, outputfile, title, authorName, chapters, periodical=False):
        self.outputfile = outputfile
        self.title = title
        self.authorName = authorName
        self.chapters = chapters
        self.periodical = periodical

    def writeMimeTypeFile(self, zipFile):
        zipFile.writestr('mimetype', 'application/epub+zip')

    def writeChapterToEpub(self, chapterId, chapter, epub):
        chapterText = u'''<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
  <head>
    <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8" />
    <title>%s</title>
</head>
  <body>
%s
  </body>
</html>''' % (chapter['title'], chapter['body'])
        chapter['filename'] = 'chapter-%s.html' % (chapterId, )
        chapter['id'] = 'chapter-%s' % (chapterId, )
        epub.writestr('OEBPS/chapter-%s.html' % (chapterId, ), chapterText.encode('utf-8'))

    def writeBookFile(self):
        opf = OpfFile(self.title, self.authorName, self.periodical)
        containerFile = ContainerFile()
        ncx = NcxFile(self.title, self.authorName, self.periodical)
        epub = ZipFile(self.outputfile, 'w')
        if self.periodical:
            i = 0
            for section in self.chapters:
                for chapter in section['chapters']:
                    self.writeChapterToEpub(i, chapter, epub)
                    i += 1
        else:
            for i, chapter in enumerate(self.chapters):
                self.writeChapterToEpub(i, chapter, epub)

        ncx.writeToEpub(self.chapters, epub)
        opf.writeToEpub(self.chapters, epub)
        self.writeMimeTypeFile(epub)
        containerFile.finish(epub)
        epub.close()
