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
	from pymysql.err import InternalError
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
			try:
				super(Connection,self).query( sql, args=args )
			except InternalError as e:

				if e.args == (0, 'Socket receive buffer full'):
					# This is very similar to https://github.com/esnme/ultramysql/issues/16
					# (although that issue is claimed to be fixed).
					# It causes issues when using the same connection to execute very
					# many requests (in one example, slightly more than 2,630,000 queries).
					# Most commonly, it has been seen when attempting a database
					# pack or conversion on a large database. In that case, the MySQL-Python
					# driver must be used, or the amount of data to query must otherwise
					# be reduced.

					# In theory, we can workaround the issue by replacing our now-bad _umysql_conn
					# with a new one and trying again.
					assert not self._umysql_conn.is_connected()
					self._umysql_conn.close()
					del self._umysql_conn
					import umysql
					self._umysql_conn = umysql.Connection()
					self._connect() # Potentially this could raise again?
					try:
						return self.query(sql, args)
					except InternalError:
						raise
						# However, in practice, this results in raising the same
						# error with 2.61 of umysql; it's not clear why that is, but
						# something seems to be holding on to the errno

				raise



	# Patching the module itself seems to be not needed because
	# RelStorage uses 'mysql.Connect' directly. And if we patch the module,
	# we get into recursive super calls
	#umysqldb.connections.Connection = Connection
	# Also patch the re-export of it
	umysqldb.connect = Connection
	umysqldb.Connection = Connection
	umysqldb.Connect = Connection

	# Error handling used to work like this:
	#
	# - A Connection has an errorhandler (NOTE: as of 0.6, pymysql no
	# longer does)
	#
	# - A Cursor copies the Connection's errorhandler; both of these
	# direct unexpected exceptions through the error handler.
	#
	# - pymysql's connections use pymysql.err.defaulterrorhandler,
	# which translates anything that is NOT a subclass of
	# pymysql.err.Error into that class (NOTE: as of 0.6, this is
	# gone)

	# umysql contains its own mapping layer and expects that to all
	# happen before the errorhandler gets called, which in turn simply
	# raises the error again
	if Connection.errorhandler.im_func is not umysqldb.connections.defaulterrorhandler:
		raise ImportError("Internals of umysqldb have changed")

	# However, as of 0.6, PyMySQL removed support for the connection-level
	# errorhandler attribute, which was in turn copied to the cursor
	# (See https://github.com/PyMySQL/PyMySQL/commit/e8ae4ce8812392c993d5029a5ccbf5667310b3fa)
	# Released versions of umysqldb as of 2013-10-08 still use
	# this attribute on the cursor, leading to attribute errors.
	# Nothing was ever setting this on a connection, so we can statically
	# set it ourself.
	if hasattr(umysqldb.cursors.Cursor, 'errorhandler'):
		raise ImportError("Internals of umysqldb have changed")

	# The problem is that some errors are not mapped appropriately. In
	# particular, IOError is prone to escaping as-is, which relstorage
	# isn't expecting, thus defeating its try/except blocks.
	#
	# Now that pymysql doesn't have complex behaviour possible,
	# the simplest thing to do as to adjust mapping in our own
	# errorhandler when needed
	from pymysql.err import Error,InterfaceError,DatabaseError
	import sys
	def defaulterrorhandler(connection, cursor, errorclass, errorvalue):
		del cursor
		del connection

		# IOErrors get mapped to InterfaceError
		# if they get here
		if issubclass(errorclass,IOError):
			raise InterfaceError(errorclass, errorvalue)

		if not issubclass(errorclass, Error):
			raise Error(errorclass, errorvalue)

		if isinstance(errorvalue, errorclass):
			# saving stacktrace when errorhandler is called in catch
			if sys.exc_info()[1] is errorvalue:
				raise
			raise errorvalue

		raise errorclass(errorvalue)

	Connection.errorhandler = defaulterrorhandler
	# Because of how this is called, we can't just copy it from
	# Connection or we get the wrong kind of bound method
	umysqldb.cursors.Cursor.errorhandler = defaulterrorhandler

	# Now got to patch relstorage to recognize some exceptions. If these
	# don't get caught, relstorage may not properly close the connection, or fail
	# to recognize that the connection is already closed
	import relstorage.adapters.mysql
	assert relstorage.adapters.mysql.MySQLdb is umysqldb

	for attr in (relstorage.adapters.mysql,
				 relstorage.adapters.mysql.MySQLdbConnectionManager ):
		# close_exceptions: "to ignore when closing the connection"
		attr.close_exceptions += (pymysql.err.Error, # The one usually mapped to
								  IOError, # This one can escape mapping
								  DatabaseError)

	for attr in (relstorage.adapters.mysql,
				 relstorage.adapters.mysql.MySQLdbConnectionManager):
		# disconnected_exceptions: "indicates the connection is disconnected"

		# Note we don't make the generic `pymysql.err.Error` indicate
		# disconnection
		attr.disconnected_exceptions += (IOError, # This one can escape mapping;
										 # This one has only been seen as its subclass,
										 # InternalError, as (0, 'Socket receive buffer full'),
										 # which should probably be taken as disconnect
										 DatabaseError,
										 )

	from . import relstorage_timestamp_repr_patch_on_import
	relstorage_timestamp_repr_patch_on_import.patch()
	from . import relstorage_zlibstorage_patch_on_import
	relstorage_zlibstorage_patch_on_import.patch()
	from . import relstorage_explicitly_close_memcache_patch_on_import
	relstorage_explicitly_close_memcache_patch_on_import.patch()

_patch()

def patch():
	pass
