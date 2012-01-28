#!/usr/bin/env python2.7

import cgi
import os
import sys

# Defer non-required imports to later to speed startup time
if sys.platform == 'darwin':
	import cgitb
	cgitb.enable()


DB_FILE = os.path.expanduser( "~/database/address.sqlite3" )
STATEMENT = "INSERT INTO ADDRS VALUES (?)"

class InMemFieldStorage(cgi.FieldStorage):

	def make_file(self, *args, **kwargs):
		import tempfile
		return tempfile.SpooledTemporaryFile('w+b')

fieldstorage = InMemFieldStorage()
value = ''
if fieldstorage.file:
	value = fieldstorage.value
elif os.environ['REQUEST_METHOD'] == 'POST' and 'email' in fieldstorage:
	value = fieldstorage['email'].value

# 100 char max
addr = value[0:min(len(value), 100)]
if addr:
	import sqlite3
	with sqlite3.connect( DB_FILE ) as conn:
		conn.execute( STATEMENT, (addr,) )

print 'Content-Type: text/plain'
if os.environ.get( 'HTTP_REFERER' ) and value:
	print 'Status: 301 Moved'
	# Let them know they subscribed. We're assuming it comes from
	# a URL that doesn't have a query already
	#print 'Location:', (os.environ['HTTP_REFERER'] + '?subscribed=true')
	print 'Location: http://nextthought.com/thankyou.html?subscribed=true'
	print
else:
	print

	print ('Subscribed ' + addr) if value else 'Not subscribed'

