#!/usr/local/bin/python
#
#  Simple Python (2.7.2) program that fetches bookmarks from your delicious account
#  and imports it into your pinboard account.
#
#  Created this (my first python program, so it probably sucks, but it works!) after 
#  getting repeated 'read failed' errors when trying to import my delicious export html
#  file into pinboard.
#
#  Whilst writing and testing this, noticed that the delicious api was returning empty
#  description (title) values which are required by pinboard, which may have been the 
#  original culprit.  This program attempts to get the title from the original page
#  resource itself.  If that fails, the title is set to 'default' as a last resort.
#
#  Program parameters:
#     1. delicious username
#     2. delicous password
#     3. pinboard username
#     4. pinboard password
#     5. verbose (Y/N)
#
#  e.g. ./import.py dusr dpwd pusr ppwd Y
#
#  NOTE: 
#     1. If title cannot be scraped from online resource, it's set to 'default'.
#     2. If title contains non-ascii unicode characters these are not translated but ignored. 
#     3. Added a 9 second delay between pinboard bookmark posts to prevent throttling. This 
#        is 3 times longer than what the pinboard API docs suggest, to be on the safe side.
#
import base64
import httplib
import lxml.html
import sys
import time
import urllib
import urllib2
import xml.etree.ElementTree as ET

user_agent = 'Bookmarks-Import-App'
pinboard_rate_limit = 9

delicious_username = sys.argv[1]
delicious_password = sys.argv[2]
pinboard_username = sys.argv[3]
pinboard_password = sys.argv[4]
verbose = True if sys.argv[5] == 'Y' else False

class PinboardBookmark:
   def __init__(self, url, description, extended, tags, dt, private):
      self.url = urllib.quote(url)
      self.description = description

      # as of this writing delicious API is not including titles in responses for some reason
      # so we have to try and get these ourselves by scraping it directly from the resource
      if len(self.description) == 0:
         try:
            self.description = lxml.html.parse(url).find('.//title').text
         except:
            if verbose:
               print 'Error getting title for', url, '(so using default)', sys.exc_info()[0]
            self.description = 'default'

      # encoding title to ascii for inclusion as URL param 
      # and ignoring translation of any non-ascii characters
      self.description = self.description.encode('ascii', 'ignore')
      self.description = urllib.quote(self.description)
      
      self.extended = extended
      if len(self.extended) > 0:
         self.extended = self.extended.encode('ascii', 'ignore')
         self.extended = urllib.quote(self.extended)

      self.tags = tags
      if len(self.tags) > 0:
         self.tags = self.tags.encode('ascii', 'ignore')
         self.tags = urllib.quote(tags)

      self.dt = dt
      if len(self.dt) > 0:
         self.dt = self.dt.encode('ascii', 'ignore')
         self.dt = urllib.quote(dt)

      self.shared = 'no' if private == 'yes' else 'yes'

   def print_bookmark(self):
      print 'Pinboard Bookmark: url: %s; title: %s; description: %s; tags: %s; dt: %s; shared: %s' % (self.url, 
         self.description, self.extended, self.tags, self.dt, self.shared)
      print

   def add(self):
      uri = 'https://api.pinboard.in/v1/posts/add?url=%s&description=%s&extended=%s&tags=%s&dt=%s&shared=%s' % (self.url,
         self.description, self.extended, self.tags, self.dt, self.shared)
      request = urllib2.Request(uri)
      request.add_header('User-Agent', user_agent)
      request.add_header('Authorization', 'Basic ' + base64.b64encode('%s:%s' % (pinboard_username, pinboard_password)))
      opener = urllib2.build_opener()
      try:
         response = opener.open(request).read()
      except urllib2.HTTPError as e:
         print e.code
         print e.read()
         return
      if verbose:
         print response

# Returns URI for *all* your bookmarks from delicious!
def build_delicious_request(user, pwd):
   uri = 'https://api.delicious.com/v1/posts/all'
   request = urllib2.Request(uri)
   request.add_header('User-Agent', user_agent)
   request.add_header('Authorization', 'Basic ' + base64.b64encode('%s:%s' % (user, pwd)))
   return request

def do_pinboard_import():
   delicious_request = build_delicious_request(delicious_username, delicious_password)
   opener = urllib2.build_opener()

   try:   
      bookmarksXML = opener.open(delicious_request).read()
   except urllib2.HTTPError as e:
      print e.code
      print e.read()
      return

   root = ET.fromstring(bookmarksXML)
   
   for child in root:
      pbookmark = PinboardBookmark(child.get('href'),
         child.get('description'),
         child.get('extended'),
         child.get('tag'),
         child.get('time'),
         child.get('private'))

      if verbose:
         pbookmark.print_bookmark()
      
      pbookmark.add()
      # add delay between requests for pinboard's benefit
      time.sleep(pinboard_rate_limit)

def main():
   print 'Starting import...'   
   do_pinboard_import()
   print 'Import complete.'
   return

if __name__ == '__main__':
   main()
