#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Monkey-patch for RelStorage to use pure-python drivers that are non-blocking.

Also, while we're monkeying with database drivers, adjusts the set of
retriable exceptions that zope.sqlalchemy knows about.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

def _patch():
	try:
		import umysqldb
		import umysql
		assert umysql  # not used here, but must be importable for this to work
		umysqldb.install_as_MySQLdb()
	except ImportError:
		import platform
		py_impl = getattr(platform, 'python_implementation', lambda: None)
		if py_impl() == 'PyPy':
			import pymysql
			pymysql.install_as_MySQLdb()
			umysqldb = pymysql
		else:
			raise

	_patch_connection()
	_patch_relstorage_error(umysqldb)
	_patch_transaction_retry()

def _patch_connection():

	# The underlying umysql driver doesn't handle dicts as arguments
	# to queries (as of 2012-09-13). Until it does, we need to do that
	# because RelStorage uses that in a few places
	try:
		from umysqldb.connections import encoders, notouch
		import umysqldb.connections
		import umysql
		import sys
	except ImportError:
		return

	# Error handling used to work like this:
	#
	# - A Connection has an errorhandler (NOTE: as of 0.6, pymysql no
	# longer does and as of 1.0.4dev2 neither does umysqldb)
	#
	# - A Cursor copies the Connection's errorhandler; both of these
	# direct unexpected exceptions through the error handler.
	#
	# - pymysql's connections use pymysql.err.defaulterrorhandler,
	# which translates anything that is NOT a subclass of
	# pymysql.err.Error into that class (NOTE: as of 0.6, this is
	# gone)
	# That's all gone now.

	# umysql contains its own mapping layer which first goes through
	# pymysl.err.error_map, but that only handles a very small number
	# of errors. First, umysql errors get mapped to a subclass of pymysql.err.Error,
	# either an explicit one or OperationalError or InternalError.

	# Next, RuntimeError subclasses get mapped to ProgrammingError
	# or stay as is.

	# The problem is that some errors are not mapped appropriately. In
	# particular, IOError is prone to escaping as-is, which relstorage
	# isn't expecting, thus defeating its try/except blocks.

	# We must catch that here. There may be some other things we
	# want to catch and map, but we'll do that on a case by case basis
	# (previously, we mapped everything to Error, which may have been
	# hiding some issues)

	from pymysql.err import InternalError, InterfaceError
	class Connection(umysqldb.connections.Connection):

		def __debug_lock(self, sql, ex=False):
			if not 'GET_LOCK' in sql:
				return

			logger = __import__('logging').getLogger(__name__)

			try:
				result = self._result
				if result is None:
					logger.warn("No result from GET_LOCK query: %s", result.__dict__, exc_info=ex)
					return
				if not result.affected_rows:
					logger.warn("Zero rowcount from GET_LOCK query: %s", result.__dict__, exc_info=ex)
				if not result.rows:
					# We see this a fair amount. The C code in umysql got a packet that
					# its treating as an "OK" response, for which it just returns a tuple
					#   (affected_rows, rowid)
					# But no actual rows. In all cases, it has been returning affected_rows of 2?
					# We *could* patch the rows variable here to be [0], indicating the lock was not
					# taken, but given that OK response I'm not sure that's right just yet
					logger.warn("Empty rows from GET_LOCK query: %s", result.__dict__, exc_info=ex)
			except Exception:
				logger.exception("Failed to debug lock problem")

		def decode(self, value):
			# PyMySQL 0.7 `pymysql.Binary()` returns `bytearray` on Python 2.
			# The underlying umysql driver doesn't handle bytearray it expects str
			if isinstance(value, bytearray):
				value = str(value)
			return value

		def query(self, sql, args=()):
			__traceback_info__ = args
			if isinstance(args, dict):
				# First, encode them as strings
				args = {k: encoders.get(type(v), notouch)(v) for k, v in args.items()}
				# now format the string
				sql = sql % args
				# and delete the now useless args
				args = ()
			if isinstance(args, (list, tuple)) and args:
				args = map(self.decode, args)

			try:
				super(Connection, self).query(sql, args=args)
				self.__debug_lock(sql)
			except IOError:
				self.__debug_lock(sql, True)
				tb = sys.exc_info()[2]
				raise InterfaceError, None, tb
			except InternalError as e:
				self.__debug_lock(sql, True)
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
					self._connect()  # Potentially this could raise again?
					try:
						return self.query(sql, args)
					except InternalError:
						raise
						# However, in practice, this results in raising the same
						# error with 2.61 of umysql; it's not clear why that is, but
						# something seems to be holding on to the errno

				raise
			except Exception:
				self.__debug_lock(sql, True)
				raise

		def connect(self, *args, **kwargs):
			return self._connect()

	# Patching the module itself seems to be not needed because
	# RelStorage uses 'mysql.Connect' directly. And if we patch the module,
	# we get into recursive super calls
	# umysqldb.connections.Connection = Connection
	# Also patch the re-export of it
	umysqldb.connect = Connection
	umysqldb.Connect = Connection
	umysqldb.Connection = Connection

def _patch_relstorage_error(umysqldb):
	import relstorage.adapters._mysql_drivers
	assert relstorage.adapters._mysql_drivers.MySQLdbDriver.connect is umysqldb.connect

def _patch_transaction_retry():
	# We've seen OperationalError "database has gone away (32, broken pipe)", which is a
	# subclass of DatabaseError. RelStorage is told to ignore DatabaseError,
	# so we do too.

	from pymysql.err import DatabaseError

	# As a reminder, the TransactionLoop calls transaction.manager._retryable,
	# which calls each joined resource's `should_retry` method. The
	# sqlalchemey datamanager uses this list to make that distinction
	# (if it changes, this patch will break)
	import zope.sqlalchemy.datamanager as sdm
	# tuples of class and test action or none
	sdm._retryable_errors.append((DatabaseError, None))


	# Do the same thing for the transaction loop, at the sqlalchemy
	# level. This uses sdm.SessionDataManager.should_retry
	import nti.transactions.transactions
	import functools
	sql_should_retry = functools.partial(sdm.SessionDataManager.should_retry.im_func, None)
	from sqlalchemy.exc import SQLAlchemyError
	nti.transactions.transactions.TransactionLoop._retryable_errors += ((SQLAlchemyError, sql_should_retry),)

_patch()

def patch():
	pass
