#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# Import NOW to ensure we get the right monkey patches
# Importing here, when we start from pserve/supervisor, lets
# us be sure that the transaction manager and zope.component get the
# right threading bases and we don't have to use our fancy patched classes
# (which do work, but this is safer)
# (NOTE: Now that we expect to be using nti_pserve, this should no longer be necessary)
import nti.dataserver

# Monkey-patch for RelStorage
logger = __import__('logging').getLogger(__name__)
try:
	logger.debug( "Attempting MySQL monkey patch" )
	import umysqldb
except ImportError as e:
	logger.exception( "Please 'pip install -r requirements.txt' to get non-blocking drivers." )
	# This early, logging is probably not set up
	import traceback
	import sys
	print( "Please 'pip install -r requirements.txt' to get non-blocking drivers.", file=sys.stderr )
	traceback.print_exc( e )
else:
	logger.info( "Monkey-patching the MySQL driver for RelStorage to work with gevent" )

	umysqldb.install_as_MySQLdb()

	# The underlying umysql driver doesn't handle dicts as arguments
	# to queries (as of 2012-09-13). Until it does, we need to do that
	# because RelStorage uses that in a few places

	import umysqldb.connections
	from umysqldb.connections import encoders, notouch
	class Connection(umysqldb.connections.Connection):

		def query( self, sql, args=() ):
			__traceback_info__ = args
			if isinstance( args, dict ):
				# First, encode them as strings
				args = {k: encoders.get(type(v), notouch)(v) for k, v in args.items()}
				# now format the string
				sql = sql % args
				# and delete the now useless args
				args = ()
			super(Connection,self).query( sql, args=args )

	# Patching the module itself seems to be not needed because
	# RelStorage uses 'mysql.Connect' directly. And if we patch the module,
	# we get into recursive super calls
	#umysqldb.connections.Connection = Connection
	# Also patch the re-export of it
	umysqldb.connect = Connection
	umysqldb.Connection = Connection
	umysqldb.Connect = Connection
