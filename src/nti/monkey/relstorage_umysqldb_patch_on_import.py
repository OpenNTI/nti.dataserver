#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Monkey-patch for RelStorage to use pure-python drivers that are
non-blocking.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

def _patch():
	try:
		import umysqldb
		import pymysql.err
		umysqldb.install_as_MySQLdb()
		import umysqldb.connections
		import umysqldb.cursors
	except ImportError:
		import platform
		py_impl = getattr(platform, 'python_implementation', lambda: None)
		if py_impl() == 'PyPy':
			import warnings
			warnings.warn( "Unable to use umysqldb" ) # PyPy?
			return
		raise

	# The underlying umysql driver doesn't handle dicts as arguments
	# to queries (as of 2012-09-13). Until it does, we need to do that
	# because RelStorage uses that in a few places
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


	# As of 0.6, PyMySQL removed support for the connection-level
	# errorhandler attribute, which was in turn copied to the cursor
	# (See https://github.com/PyMySQL/PyMySQL/commit/e8ae4ce8812392c993d5029a5ccbf5667310b3fa)
	# Released versions of umysqldb as of 2013-10-08 still use
	# this attribute on the cursor, leading to attribute errors.
	# Nothing was ever setting this on a connection, so we can statically
	# set it ourself. Much of the below is predicated on this errorhandler
	# behaviour
	if hasattr(umysqldb.cursors.Cursor, 'errorhandler'):
		raise ImportError("Internals of umysqldb have changed")

	umysqldb.cursors.Cursor.errorhandler = Connection.errorhandler

	# Now got to patch relstorage to recognize some exceptions. If these
	# don't get caught, relstorage may not properly close the connection, or fail
	# to recognize that the connection is already closed
	import relstorage.adapters.mysql
	assert relstorage.adapters.mysql.MySQLdb is umysqldb
	# NOTE: as-of the released version of umysqldb at 2013-01-14, the error handling
	# mapping is broken. Error handling works like this:
	# A Connection has an errorhandler
	# A Cursor copies the Connection's errorhandler; both of these direct unexpected exceptions
	# through the error handler.
	# pymysql's connections use pymysql.err.defaulterrorhandler, which translates anything
	# that is NOT a subclass of pymysql.err.Error into that class.
	# However, umysqldb's defaulterrorhandler simply raises the exception; this is because
	# many places already manually translate exceptions.
	# The problem is that while many places do, some places do not.
	# At this writing, it's not clear if the best thing to do is to add more exceptions
	# to the lists below, or try to patch defaulterrorhandler.
	# Since the more limited thing is to add more exceptions, then that's what we do.
	# (However, changing defaulterrorhandler would probably result in a higher-level exception
	# from relstorage, a POSException, which might get better handling by the transaction package.
	# TODO: Investigate that.)
	for attr in (relstorage.adapters.mysql,
				 relstorage.adapters.mysql.MySQLdbConnectionManager ):
		 # close_exceptions: "to ignore when closing the connection"
		attr.close_exceptions += (pymysql.err.Error, # The one usually mapped to
								  IOError) # This one can escape mapping

	for attr in (relstorage.adapters.mysql,
				 relstorage.adapters.mysql.MySQLdbConnectionManager):
		# disconnected_exceptions: "indicates the connection is disconnected"
		attr.disconnected_exceptions += (IOError,) # This one can escape mapping; note we don't make pymysql.err.Error indicate disconnection

	from . import relstorage_timestamp_repr_patch_on_import
	relstorage_timestamp_repr_patch_on_import.patch()
	from . import relstorage_zlibstorage_patch_on_import
	relstorage_zlibstorage_patch_on_import.patch()
_patch()

def patch():
	pass
