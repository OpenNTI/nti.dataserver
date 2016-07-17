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
	_patch_transaction_retry()

def _patch_connection():
	import umysqldb
	from relstorage.adapters._mysql_drivers import UConnection
	umysqldb.connect = UConnection
	umysqldb.Connect = UConnection
	umysqldb.Connection = UConnection

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
