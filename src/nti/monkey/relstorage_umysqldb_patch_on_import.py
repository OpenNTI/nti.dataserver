#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Monkey-patch for RelStorage to use pure-python drivers that are
non-blocking.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

def _patch_relstorage_for_newer_persistent():
	from persistent.timestamp import pyTimeStamp
	# The independent release of persistent changes repr(TimeStamp) to
	# return an actual repr of its raw data, not the raw data. This
	# is required for py3, but breaks RelStorage 1.5's assumption that
	# the repr of a timestamp is its raw data.
	# A search of the source code reveals this to only be used in relstorage.storage
	# Depending on whether the c extensions are in play, TimeStamp may
	# be a function or a type...if it is a type, we cannot actually
	# get to it reliably by name
	def _repr(o):
		if isinstance(o, pyTimeStamp) or (type(o).__name__ == 'TimeStamp' and type(o).__module__ == 'persistent'):
			return o.raw()
		return repr(o)
	import relstorage.storage
	relstorage.storage.repr = _repr

def _patch_zlibstorage_for_IMVCCStorage():
	try:
		from zc.zlibstorage import ZlibStorage
	except ImportError:
		return

	if 'new_instance' not in ZlibStorage.__dict__:
		# ZLibStorage claims to provide the same
		# interfaces as whatever it is wrapping.
		# It also passes through any methods it does not implement
		# to the storage it is wrapping.
		# If the storage it is wrapping implements IMVCCStorage, then
		# the wrapping storage provides a 'new_instance' method and
		# ZLibStorage happily claims to provide the same and passes that
		# method call through. When a transaction begins and an isolated storage
		# instance is needed, then, ZLibStorage gets dropped and we lose all
		# compression.
		# The only known implementation if IMVCCStorage is RelStorage,
		# so might as well fix that here.
		# (Sigh, this means all our databases are currently uncompressed)
		# TODO: Send this to ZODB-Dev, submit patch
		def new_instance(self):
			new_self = type(self).__new__(type(self))
			new_self.__dict__ = self.__dict__.copy()
			new_self.base = self.base.new_instance()
			return new_self
		ZlibStorage.new_instance = new_instance
		print( "Patched zlibstorage to work with relstorage." )



def _patch():
	try:
		import umysqldb
		import pymysql.err
		umysqldb.install_as_MySQLdb()
		import umysqldb.connections
	except ImportError:
		import sys
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

	_patch_relstorage_for_newer_persistent()
	_patch_zlibstorage_for_IMVCCStorage()
_patch()

def patch():
	pass
