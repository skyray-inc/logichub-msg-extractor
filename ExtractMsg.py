#!/usr/bin/env python
# -*- coding: latin-1 -*-
"""
ExtractMsg:
    Extracts emails and attachments saved in Microsoft Outlook's .msg files

https://github.com/mattgwwalker/msg-extractor
"""

__author__ = 'Matthew Walker & The Elemental of Creation'
__date__ = '2018-05-22'
__version__ = '0.8'
# --- LICENSE -----------------------------------------------------------------
#
#    Copyright 2013 Matthew Walker
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import copy
import re
import sys
import glob
import traceback
import struct
import datetime
from email.parser import Parser as EmailParser
import email.utils
import olefile as OleFile
import json
from imapclient.imapclient import decode_utf7
import random
import string

# This property information was sourced from
# http://www.fileformat.info/format/outlookmsg/index.htm
# on 2013-07-22.
# It was extened by The Elemental of Creation on 2018-04-03
properties = {
    '001A': 'Message class',
    '0037': 'Subject',
    '003D': 'Subject prefix',
    '0040': 'Received by name',
    '0042': 'Sent repr name',
    '0044': 'Rcvd repr name',
    '004D': 'Org author name',
    '0050': 'Reply rcipnt names',
    '005A': 'Org sender name',
    '0064': 'Sent repr adrtype',
    '0065': 'Sent repr email',
    '0070': 'Topic',
    '0075': 'Rcvd by adrtype',
    '0076': 'Rcvd by email',
    '0077': 'Repr adrtype',
    '0078': 'Repr email',
    '007d': 'Message header',
    '0C1A': 'Sender name',
    '0C1E': 'Sender adr type',
    '0C1F': 'Sender email',
    '0E02': 'Display BCC',
    '0E03': 'Display CC',
    '0E04': 'Display To',
    '0E1D': 'Subject (normalized)',
    '0E28': 'Recvd account1 (uncertain)',
    '0E29': 'Recvd account2 (uncertain)',
    '1000': 'Message body',
    '1008': 'RTF sync body tag',
    '1009': 'Compressed RTF body',
    '1013': 'HTML body',
    '1035': 'Message ID (uncertain)',
    '1046': 'Sender email (uncertain)',
    '3001': 'Display name',
    '3002': 'Address type',
    '3003': 'Email address',
    '39FE': '7-bit email (uncertain)',
    '39FF': '7-bit display name',

    # Attachments (37xx)
    '3701': 'Attachment data',
    '3703': 'Attachment extension',
    '3704': 'Attachment short filename',
    '3707': 'Attachment long filename',
    '370E': 'Attachment mime tag',
    '3712': 'Attachment ID (uncertain)',

    # Address book (3Axx):
    '3A00': 'Account',
    '3A02': 'Callback phone no',
    '3A05': 'Generation',
    '3A06': 'Given name',
    '3A08': 'Business phone',
    '3A09': 'Home phone',
    '3A0A': 'Initials',
    '3A0B': 'Keyword',
    '3A0C': 'Language',
    '3A0D': 'Location',
    '3A11': 'Surname',
    '3A15': 'Postal address',
    '3A16': 'Company name',
    '3A17': 'Title',
    '3A18': 'Department',
    '3A19': 'Office location',
    '3A1A': 'Primary phone',
    '3A1B': 'Business phone 2',
    '3A1C': 'Mobile phone',
    '3A1D': 'Radio phone no',
    '3A1E': 'Car phone no',
    '3A1F': 'Other phone',
    '3A20': 'Transmit dispname',
    '3A21': 'Pager',
    '3A22': 'User certificate',
    '3A23': 'Primary Fax',
    '3A24': 'Business Fax',
    '3A25': 'Home Fax',
    '3A26': 'Country',
    '3A27': 'Locality',
    '3A28': 'State/Province',
    '3A29': 'Street address',
    '3A2A': 'Postal Code',
    '3A2B': 'Post Office Box',
    '3A2C': 'Telex',
    '3A2D': 'ISDN',
    '3A2E': 'Assistant phone',
    '3A2F': 'Home phone 2',
    '3A30': 'Assistant',
    '3A44': 'Middle name',
    '3A45': 'Dispname prefix',
    '3A46': 'Profession',
    '3A48': 'Spouse name',
    '3A4B': 'TTYTTD radio phone',
    '3A4C': 'FTP site',
    '3A4E': 'Manager name',
    '3A4F': 'Nickname',
    '3A51': 'Business homepage',
    '3A57': 'Company main phone',
    '3A58': 'Childrens names',
    '3A59': 'Home City',
    '3A5A': 'Home Country',
    '3A5B': 'Home Postal Code',
    '3A5C': 'Home State/Provnce',
    '3A5D': 'Home Street',
    '3A5F': 'Other adr City',
    '3A60': 'Other adr Country',
    '3A61': 'Other adr PostCode',
    '3A62': 'Other adr Province',
    '3A63': 'Other adr Street',
    '3A64': 'Other adr PO box',

    '3FF7': 'Server (uncertain)',
    '3FF8': 'Creator1 (uncertain)',
    '3FFA': 'Creator2 (uncertain)',
    '3FFC': 'To email (uncertain)',
    '403D': 'To adrtype (uncertain)',
    '403E': 'To email (uncertain)',
    '5FF6': 'To (uncertain)'}

if sys.version_info[0] >= 3:  # Python 3
    def windowsUnicode(string):
        if string is None:
            return None
        return str(string, 'utf_16_le')


    stri = [str]


    def properHex(inp):
        a = ''
        if type(inp) in stri:
            a = ''.join([hex(ord(inp[x]))[2:].rjust(2, '0') for x in range(len(inp))])
        if type(inp) == bytes:
            a = inp.hex()
        elif type(inp) == int:
            a = hex(inp)[2:]
        if len(a) % 2 != 0:
            a = '0' + a
        return a


    def encode(inp):
        return inp
else:  # Python 2
    def windowsUnicode(string):
        if string is None:
            return None
        return unicode(string, 'utf_16_le')


    stri = [str, unicode]


    def properHex(inp):
        a = ''
        if type(inp) in stri:
            a = ''.join([hex(ord(inp[x]))[2:].rjust(2, '0') for x in range(len(inp))])
        elif type(inp) == int:
            a = hex(inp)[2:]
        elif type(inp) == long:
            a = hex(inp)[2:-1]
        if len(a) % 2 != 0:
            a = '0' + a
        return a


    def encode(inp):
        return inp.encode('utf8')


def msgEpoch(inp):
    ep = 116444736000000000
    return (inp - ep) / 10000000.0


def xstr(s):
    if s is None:
        return ''
    if isinstance(s, unicode):
        return s.encode('utf-8')
    elif isinstance(s, str):
        return bytes(s).decode('utf-8', 'ignore').encode('utf-8')
    else:
        raise Exception('unknown type for s' + str(type(s)))



def addNumToDir(dirName):
    # Attempt to create the directory with a '(n)' appended
    for i in range(2, 100):
        try:
            newDirName = dirName + ' (' + str(i) + ')'
            os.makedirs(newDirName)
            return newDirName
        except Exception as e:
            pass
    return None


fromTimeStamp = datetime.datetime.fromtimestamp


class Attachment:
    def __init__(self, msg, dir_):
        self.msg = msg
        self.__dir = dir_
        # Get long filename
        self.longFilename = msg._getStringStream([dir_, '__substg1.0_3707'])

        # Get short filename
        self.shortFilename = msg._getStringStream([dir_, '__substg1.0_3704'])

        # Get Content-ID
        self.cid = msg._getStringStream([dir_, '__substg1.0_3712'])

        # Get attachment data
        if msg.Exists([dir_, '__substg1.0_37010102']):
            self.__type = 'data'
            self.data = msg._getStream([dir_, '__substg1.0_37010102'])
        elif msg.Exists([dir_, '__substg1.0_3701000D']):
            if self.props.has_key('37050003') and (self.props['37050003'].value & 0x7) != 0x5:
                raise NotImplementedError(
                    'Current version of ExtractMsg.py does not support extraction of containers that are not embeded msg files.')
                # TODO add implementation
            self.__prefix = msg.prefixList + [dir_, '__substg1.0_3701000D']
            self.data = msg._getStream([dir_, '__substg1.0_37020102'])
            self.__type = 'msg'
        else:
            raise Exception('Unknown file type')

    def saveEmbededMessage(self, contentId=False, json=False, useFileName=False, raw=False):
        """
        Seperate function from save to allow it to
        easily be overridden by a subclass
        """
        msg = Message(self.msg.path, self.__prefix)
        a = msg.save(useFileName, raw, contentId)
        return a

    def save(self, directory=os.path.expanduser('~/scratch/results/'), contentId=False, json=False, useFileName=False, raw=False,
             stuff=None):
        # Use long filename as first preference
        try:
            os.mkdir(directory)
        except OSError:
            pass
        b = []
        filename = self.longFilename
        # Check if user wants to save the file under the Content-id
        if contentId:
            filename = self.cid
        # Otherwise use the short filename
        if filename is None:
            filename = self.shortFilename
        # Otherwise just make something up!
        if filename is None:
            filename = 'UnknownFilename ' + \
                       ''.join(random.choice(string.ascii_uppercase + string.digits)
                               for _ in range(5)) + '.bin'
        if self.__type == "data":
            f = open(directory + filename, 'wb')
            f.write(self.data)
            f.close()
            return filename
        else:
            a = self.saveEmbededMessage(contentId, json, useFileName, raw)
            return a

    @property
    def props(self):
        try:
            return self.__props
        except:
            self.__props = Properties(
                self.msg._getStream(self.msg.prefixList + [self.__dir, '__properties_version1.0']))
            return self.__props


class Properties:
    def __init__(self, stream, skip=None):
        self.__stream = stream
        self.__pos = 0
        if stream is not None:
            self.__len = len(stream)
        else:
            self.__len = 0
        self.__props = {}
        if skip != None:
            self.__parse(skip)
        else:
            # This section of the skip handling is not very good.
            # While it does work, it is likely to create extra
            # properties that are created from the properties file's
            # header data. While that won't actually mess anything
            # up, it is far from ideal. Basically, this is the dumb
            # skip length calculation
            self.__parse(self.__len % 16)

    def __parse(self, skip):
        if self.__pos != 0:
            return
        self.__pos += skip
        # TODO implement smart header length calculation

        while self.__pos < self.__len:
            a = Prop(self.__stream[self.__pos:self.__pos + 16])
            self.__pos += 16
            self.__props[a.name] = a

    def get(self, name):
        return self.props[name]

    def has_key(self, key):
        self.props.has_key(key)

    def items(self):
        return self.props.items()

    def iteritems(self):
        return self.props.iteritems()

    def iterkeys(self):
        return self.props.iterkeys()

    def itervalues(self):
        return self.props.itervalues()

    def keys(self):
        return self.props.keys()

    def values(self):
        return self.props.values()

    def viewitems(self):
        return self.props.viewitems()

    def viewkeys(self):
        return self.props.viewkeys()

    def viewvalues(self):
        return self.props.viewvalues()

    def __contains__(self, key):
        self.props.__contains__(key)

    def __iter__(self):
        return self.props.__iter__()

    def __getitem__(self, key):
        return self.props.__getitem__(key)

    def __len__(self):
        return len(self.__props)

    @property
    def props(self):
        return copy.deepcopy(self.__props)


class Prop:
    def __init__(self, string):
        n = string[0:4][::-1]
        self.__name = properHex(n).upper()
        self.__type, self.__value = struct.unpack('<IQ', string[4:16])

    @property
    def type(self):
        return self.__type

    @property
    def name(self):
        return self.__name

    @property
    def value(self):
        return self.__value


class Recipient:
    def __init__(self, num, msg):
        self.__msg = msg  # Allows calls to original msg file
        self.__dir = '__recip_version1.0_#{0}'.format(num.rjust(8, '0'))
        self.__props = Properties(msg._getStream(self.__dir + '/__properties_version1.0'))
        self.__email = msg._getStringStream(self.__dir + '/__substg1.0_39FE')
        self.__name = msg._getStringStream(self.__dir + '/__substg1.0_3001')
        self.__type = self.__props.get('0C150003').value
        self.__formatted = '{0} <{1}>'.format(self.__name, self.__email)

    @property
    def type(self):
        return self.__type

    @property
    def name(self):
        return self.__name

    @property
    def email(self):
        return self.__email

    @property
    def formatted(self):
        return self.__formatted

    @property
    def props(self):
        return self.__props


class Message(OleFile.OleFileIO):
    def __init__(self, filename, prefix='', attachmentClass=Attachment):
        """
        `prefix` is used for extracting embeded msg files
            inside the main one. Do not set manually unless
            you know what you are doing.

        `attachmentClass` is the class the Message object
            will use for attachments. You probably should
            not change this value unless you know what you
            are doing.

        """
        # print(prefix)
        # WARNING DO NOT MANUALLY MODIFY PREFIX. Let the program set it.
        self.__path = filename
        self.__attachmentClass = attachmentClass
        OleFile.OleFileIO.__init__(self, filename)
        prefixl = []
        if prefix != '':
            if type(prefix) not in stri:
                try:
                    prefix = '/'.join(prefix)
                except:
                    raise TypeException('invalid prefix type {}'.format(type(prefix)))
            prefix = prefix.replace('\\', '/')
            g = prefix.split("/")
            if g[-1] == '':
                g.pop()
            prefixl = g
            if prefix[-1] != '/':
                prefix += '/'
            filename = self._getStringStream(prefixl[:-1] + ['__substg1.0_3001'], prefix=False)
        self.__prefix = prefix
        self.__prefixList = prefixl
        self.filename = filename
        # Initialize properties in the order that is least likely to cause bugs.
        # TODO have each function check for initialization of needed data so these
        # lines will be unnecessary.
        self.mainProperties
        self.recipients
        self.attachments
        self.to
        self.cc
        self.sender
        self.header
        self.date
        self.__crlf = '\n'  # This variable keeps track of what the new line character should be
        self.body

    def listDir(self, streams=True, storages=False):
        temp = self.listdir(streams, storages)
        if self.__prefix == '':
            return temp
        prefix = self.__prefix.split('/')
        if prefix[-1] == '':
            prefix.pop()
        out = []
        for x in temp:
            good = True
            if len(x) <= len(prefix):
                good = False
            if good:
                for y in range(len(prefix)):
                    if x[y] != prefix[y]:
                        good = False
            if good:
                out.append(x)
        return out

    def Exists(self, inp):
        if isinstance(inp, list):
            inp = self.__prefixList + inp
        else:
            inp = self.__prefix + inp
        return self.exists(inp)

    def _getStream(self, filename, prefix=True):
        if isinstance(filename, list):
            filename = '/'.join(filename)
        if prefix:
            filename = self.__prefix + filename
        if self.exists(filename):
            stream = self.openstream(filename)
            return stream.read()
        else:
            return None

    def _getStringStream(self, filename, prefer='unicode', prefix=True):
        """Gets a string representation of the requested filename.
        Checks for both ASCII and Unicode representations and returns
        a value if possible.  If there are both ASCII and Unicode
        versions, then the parameter /prefer/ specifies which will be
        returned.
        """

        if isinstance(filename, list):
            # Join with slashes to make it easier to append the type
            filename = '/'.join(filename)

        asciiVersion = self._getStream(filename + '001E', prefix)
        unicodeVersion = windowsUnicode(self._getStream(filename + '001F', prefix))
        if asciiVersion is None:
            return unicodeVersion
        elif unicodeVersion is None:
            return asciiVersion
        else:
            if prefer == 'unicode':
                return unicodeVersion
            else:
                return asciiVersion

    @property
    def path(self):
        return self.__path

    @property
    def prefix(self):
        return self.__prefix

    @property
    def prefixList(self):
        return self.__prefixList

    @property
    def subject(self):
        try:
            return self._subject
        except:
            self._subject = encode(self._getStringStream('__substg1.0_0037'))
            return self._subject

    @property
    def header(self):
        try:
            return self._header
        except Exception:
            headerText = self._getStringStream('__substg1.0_007D')
            if headerText is not None:
                self._header = EmailParser().parsestr(headerText)
                self._header['date'] = self.date
            else:
                header = {
                    'date': self.date,
                    'from': self.sender,
                    'to': self.to,
                    'cc': self.cc
                }
                self._header = header
            return self._header

    def headerInit(self):
        try:
            self._header
            return True
        except:
            return False

    @property
    def mainProperties(self):
        try:
            return self._prop
        except:
            self._prop = Properties(self._getStream('__properties_version1.0'))
            return self._prop

    @property
    def date(self):
        # Get the message's header and extract the date
        try:
            return self._date
        except:
            self._date = fromTimeStamp(msgEpoch(self._prop.get('00390040').value)).__format__(
                '%a, %d %b %Y %H:%M:%S GMT %z')
            return self._date

    @property
    def parsedDate(self):
        return email.utils.parsedate(self.date)

    @property
    def sender(self):
        try:
            return self._sender
        except Exception:
            # Check header first
            if self.headerInit():
                headerResult = self.header['from']
                if headerResult is not None:
                    self._sender = headerResult
                    return headerResult
            # Extract from other fields
            text = self._getStringStream('__substg1.0_0C1A')
            email = self._getStringStream(
                '__substg1.0_5D01')  # Will not give an email address sometimes. Seems to exclude the email address if YOU are the sender.
            result = None
            if text is None:
                result = email
            else:
                result = text
                if email is not None:
                    result = result + ' <' + email + '>'

            self._sender = result
            return result

    @property
    def to(self):
        try:
            return self._to
        except Exception:
            # Check header first
            if self.headerInit():
                headerResult = self.header['to']
                if headerResult is not None:
                    self._to = headerResult
            else:
                f = []
                for x in self.recipients:
                    if x.type & 0x0000000f == 1:
                        f.append(x.formatted)
                if len(f) > 0:
                    st = f[0]
                    if len(f) > 1:
                        for x in range(1, len(f)):
                            st = st + '; {0}'.format(f[x])
                    self._to = st
                else:
                    self._to = None
            return self._to

    @property
    def compressedRtf(self):
        try:
            return self._compressedRtf
        except Exception:
            self._compressedRtf = self._getStream('__substg1.0_10090102')
            return self._compressedRtf

    @property
    def htmlBody(self):
        try:
            return self._htmlBody
        except Exception:
            self._htmlBody = self._getStream('__substg1.0_10130102')
            return self._htmlBody

    @property
    def cc(self):
        try:
            return self._cc
        except Exception:
            # Check header first
            if self.headerInit():
                headerResult = self.header['cc']
                if headerResult is not None:
                    self._cc = headerResult
            else:
                f = []
                for x in self.recipients:
                    if x.type & 0x0000000f == 2:
                        f.append(x.formatted)
                if len(f) > 0:
                    st = f[0]
                    if len(f) > 1:
                        for x in range(1, len(f)):
                            st = st + '; {0}'.format(f[x])
                    self._cc = st
                else:
                    self._cc = None
            return self._cc

    @property
    def body(self):
        # Get the message body
        try:
            return self._body
        except Exception:
            try:
                self._body = encode(self._getStringStream('__substg1.0_1000'))
                a = re.search('\n', self._body)
                if a != None:
                    if re.search('\r\n', self._body) != None:
                        self.__crlf = '\r\n'
            except Exception:
                self._body = 'no body'
            return self._body

    @property
    def attachments(self):
        try:
            return self._attachments
        except Exception:
            # Get the attachments
            attachmentDirs = []

            for dir_ in self.listDir():
                if dir_[len(self.__prefixList)].startswith('__attach') and dir_[
                    len(self.__prefixList)] not in attachmentDirs:
                    attachmentDirs.append(dir_[len(self.__prefixList)])

            self._attachments = []
            for attachmentDir in attachmentDirs:
                self._attachments.append(self.__attachmentClass(self, attachmentDir))

            return self._attachments

    @property
    def recipients(self):
        try:
            return self._recipients
        except Exception:
            # Get the recipients
            recipientDirs = []
            for dir_ in self.listDir():
                if dir_[len(self.__prefixList)].startswith('__recip') and dir_[
                    len(self.__prefixList)] not in recipientDirs:
                    recipientDirs.append(dir_[len(self.__prefixList)])
            self._recipients = []
            for recipientDir in recipientDirs:
                self._recipients.append(Recipient(recipientDir.split('#')[-1], self))
            return self._recipients

    def save(self, toJson=True, useFileName=False, raw=False, ContentId=False):
        '''Saves the message body and attachments found in the message.  Setting toJson
        to true will output the message body as JSON-formatted text.  The body and
        attachments are stored in a folder.  Setting useFileName to true will mean that
        the filename is used as the name of the folder; otherwise, the message's date
        and subject are used as the folder name.'''

        if useFileName:
            # strip out the extension
            dirName = self.filename.split('/').pop().split('.')[0]
        else:
            # Create a directory based on the date and subject of the message
            d = self.parsedDate
            if d is not None:
                dirName = '{0:02d}-{1:02d}-{2:02d}_{3:02d}{4:02d}'.format(*d)
            else:
                dirName = 'UnknownDate'

            if self.subject is None:
                subject = '[No subject]'
            else:
                subject = ''.join(i for i in self.subject if i not in r'\/:*?"<>|')
            dirName = dirName + ' ' + subject
        oldDir = os.getcwd()
        try:
            # os.chdir(dirName)
            # Save the message body
            fext = 'json' if toJson else 'text'
            # f = open('message.' + fext, 'w')
            # From, to , cc, subject, date

            ret_messages = []
            toJson = True
            attachmentNames = []
            # Save the attachments
            for attachment in self.attachments:
                if attachment._Attachment__type == 'msg':
                    ret_messages += attachment.save()
                attachmentNames.append(attachment.save())
            if toJson:
                urls = re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', decode_utf7(self.body))
                uniq_urls = []
                for i in urls:
                    if i not in uniq_urls:
                        uniq_urls.append(i)
                emailObj = {'from': xstr(self.sender),
                            'to': xstr(self.to),
                            'cc': xstr(self.cc),
                            'subject': xstr(self.subject),
                            'date': xstr(self.date),
                            'attachments': attachmentNames,
                            'body': decode_utf7(self.body),
                            'urls': uniq_urls}
                ret_messages.append(emailObj)
                return ret_messages
            else:
                # print('From: ' + xstr(self.sender) + self.__crlf)
                # print('To: ' + xstr(self.to) + self.__crlf)
                # print('CC: ' + xstr(self.cc) + self.__crlf)
                # print('Subject: ' + xstr(self.subject) + self.__crlf)
                # print('Date: ' + xstr(self.date) + self.__crlf)
                # print('-----------------' + self.__crlf + self.__crlf)
                # print(self.body)
                return 'abc'


        except Exception as e:
            print
            e
            raise

        finally:
            # Return to previous directory
            os.chdir(oldDir)

    def saveRaw(self):
        # Create a 'raw' folder
        oldDir = os.getcwd()
        try:
            rawDir = 'raw'
            os.makedirs(rawDir)
            os.chdir(rawDir)
            sysRawDir = os.getcwd()

            # Loop through all the directories
            for dir_ in self.listdir():
                sysdir = '/'.join(dir_)
                code = dir_[-1][-8:-4]
                global properties
                if code in properties:
                    sysdir = sysdir + ' - ' + properties[code]
                os.makedirs(sysdir)
                os.chdir(sysdir)

                # Generate appropriate filename
                if dir_[-1].endswith('001E'):
                    filename = 'contents.txt'
                else:
                    filename = 'contents'

                # Save contents of directory
                f = open(filename, 'wb')
                f.write(self._getStream(dir_))
                f.close()

                # Return to base directory
                os.chdir(sysRawDir)

        finally:
            os.chdir(oldDir)

    def dump(self):
        ## Prints out a summary of the message
        print('Message')
        print('Subject:', self.subject)
        print('Date:', self.date)
        print('Body:')
        print(self.body)

    def debug(self):
        for dir_ in self.listDir():
            if dir_[-1].endswith('001E') or dir_[-1].endswith('001F'):
                print('Directory: ' + str(dir_[:-1]))
                print('Contents: ' + self._getStream(dir_))

    def save_attachments(self, contentId=False, json=False, useFileName=False, raw=False):
        """Saves only attachments in the same folder.
        """
        for attachment in self.attachments:
            attachment.save(contentId, json, useFileName, raw)


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        sys.exit()

    writeRaw = False
    toJson = True
    useFileName = False

    msgs = []

    for rawFilename in sys.argv[1:]:
        if rawFilename == '--raw':
            writeRaw = True

        if rawFilename == '--json':
            toJson = True

        if rawFilename == '--use-file-name':
            useFileName = True

        for filename in glob.glob(rawFilename):
            msg = Message(filename)
            try:
                if writeRaw:
                    msg.saveRaw()
                else:
                    msgs += msg.save(useFileName)
            except Exception as e:
                msg.debug()
                print("Error with file '" + filename + "': " +
                      traceback.format_exc())

    print(json.dumps(msgs))
