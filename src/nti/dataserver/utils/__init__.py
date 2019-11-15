#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import logging
import functools

from zope import component
from zope import interface

from zope.component.hooks import setSite
from zope.component.hooks import setHooks

from zope.configuration import xmlconfig, config

from zope.dottedname import resolve as dottedname

import zope.exceptions.log
from zope.exceptions.exceptionformatter import print_exception

from nti.dataserver._Dataserver import Dataserver
from nti.dataserver._Dataserver import MinimalDataserver

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.externalization.persistence import NoPickle

# We are often, but not always, called from main,
# so we need to be sure the relevant non-gevent
# patches are applied
import nti.monkey.patch_relstorage_all_except_gevent_on_import
nti.monkey.patch_relstorage_all_except_gevent_on_import.patch()

def _configure(self=None, set_up_packages=(), features=(), context=None, execute=True):
	# zope.component.globalregistry conveniently adds
	# a zope.testing.cleanup.CleanUp to reset the globalSiteManager
	if set_up_packages:
		if context is None:
			context = config.ConfigurationMachine()
			xmlconfig.registerCommonDirectives(context)
		for feature in features:
			context.provideFeature(feature)

		for i in set_up_packages:
			__traceback_info__ = (i, self, set_up_packages)
			if isinstance(i, tuple):
				filename = i[0]
				package = i[1]
			else:
				filename = 'configure.zcml'
				package = i

			if isinstance(package, basestring):
				package = dottedname.resolve(package)
			context = xmlconfig.file(filename, package=package,
									 context=context, execute=execute)

		return context

_user_function_failed = object()  # sentinel
class _DataserverCreationFailed(Exception): pass

def run_with_dataserver(environment_dir=None,
						function=None,
						as_main=True,
						verbose=False,
						config_features=(),
						xmlconfig_packages=(),
						context=None,
						minimal_ds=False,
						use_transaction_runner=True,
						logging_verbose_level=logging.INFO):
	"""
	Execute the `function` in the (already running) dataserver
	environment configured at `environment_dir`.

	:keyword string environment_dir: The filesystem path to a dataserver environment.
	:keyword function function: The function of no parameters to execute.
	:keyword bool as_main: If ``True`` (the default) assumes this is the main portion
		of a script and configures the complete environment appropriately, including
		setting up logging.
	:keyword bool verbose: If ``True`` (*not* the default), then logging to the console
		will be at a slightly higher level.

	:keyword xmlconfig_packages: A sequence of package objects or
		strings naming packages. These will be configured, in order,
		using ZCML. The ``configure.zcml`` package from each package
		will be loaded. Instead of a package object, each item can be
		a tuple of (filename, package); in that case, the given file
		(usually ``meta.zcml``) will be loaded from the given package. ``nti.dataserver``
		will always be configured first.

	:keyword features: A sequence of strings to be added as features
		before loading the configuration. By default, this is
		nothing; ``devmode`` is one known feature name.

	:return: The results of the `function`
	"""

	@functools.wraps(function)
	def run_user_fun_print_exception():
		"""
		Run the user-given function in the environment; print exceptions
		in this env too.
		"""
		try:
			return function()
		except Exception:
			print_exception(*sys.exc_info())
			raise

	@functools.wraps(function)  # yes, two layers, but we do wrap `function`
	def run_user_fun_transaction_wrapper():
		try:
			if not minimal_ds:
				ds = Dataserver(environment_dir)
			else:
				ds = MinimalDataserver(environment_dir)
		except Exception:
			# Reraise something we can deal with (in collusion with run), but with the
			# original traceback. This traceback should be safe.
			exc_info = sys.exc_info()
			raise _DataserverCreationFailed(exc_info[1]), None, exc_info[2]

		component.provideUtility(ds, IDataserver)
		try:
			if use_transaction_runner:
				runner = component.getUtility(IDataserverTransactionRunner)
				return runner(run_user_fun_print_exception)
			else:
				return run_user_fun_print_exception()
		except AttributeError:
			# we have seen this if the function closed the dataserver manually, but left
			# the transaction open. Committing then fails. badly.
			try:
				print_exception(*sys.exc_info())
			except:
				pass
			raise
		except Exception:
			# If we get here, we are unlikely to be able to print details from the
			# exception the transaction  will have already terminated, and any
			# __traceback_info__ objects or even the arguments to the exception are
			# possible invalid Persistent objects. Hence the need to print it up there.
			return _user_function_failed
		finally:
			component.getSiteManager().unregisterUtility(ds, IDataserver)
			try:
				ds.close()
			except:
				pass

	return run(	function=run_user_fun_transaction_wrapper, as_main=as_main,
				verbose=verbose, config_features=config_features,
				xmlconfig_packages=xmlconfig_packages, context=context,
				_print_exc=False, logging_verbose_level=logging_verbose_level)

def run(function=None, as_main=True, verbose=False, config_features=(),
		xmlconfig_packages=(), context=None, _print_exc=True,
		logging_verbose_level=logging.INFO):
	"""
	Execute the `function`, taking care to print exceptions and handle configuration.

	:keyword function function: The function of no parameters to execute.
	:keyword bool as_main: If ``True`` (the default) assumes this is the main portion
		of a script and configures the complete environment appropriately, including
		setting up logging. A failure to do this, or an exception raised from ``function``
		will exit the program.
	:keyword bool verbose: If ``True`` (*not* the default), then logging to the console will
		be at a slightly higher level.

	:keyword xmlconfig_packages: A sequence of package objects or
		strings naming packages. These will be configured, in order,
		using ZCML. The ``configure.zcml`` package from each package
		will be loaded. Instead of a package object, each item can be
		a tuple of (filename, package); in that case, the given file
		(usually ``meta.zcml``) will be loaded from the given package. ``nti.dataserver``
		will always be configured first.

	:keyword features: A sequence of strings to be added as features
		before loading the configuration. By default, this is
		nothing; ``devmode`` is one known feature name.

	:return: The results of the `function`
	"""

	if as_main:
		log_format = '[%(name)s] %(levelname)s: %(message)s'
		logging.basicConfig(level=logging.WARN if not verbose else logging_verbose_level)
		logging.root.handlers[0].setFormatter(zope.exceptions.log.Formatter(log_format))

		setHooks()
		if context is None:
			packages = ['nti.dataserver']
			packages.extend(xmlconfig_packages)
		else:
			packages = xmlconfig_packages
		try:
			_configure(set_up_packages=packages, features=config_features, context=context)
		except Exception:
			print_exception(*sys.exc_info())
			sys.exit(5)

	if _print_exc:
		@functools.wraps(function)
		def fun():
			"""
			Run the user-given function in the environment; print exceptions
			in this env too.
			"""
			try:
				return function()
			except Exception:
				print_exception(*sys.exc_info())
				raise
	else:
		fun = function

	_user_ex = None
	_user_ex_str = None
	_user_ex_repr = None
	try:
		result = fun()
	except _DataserverCreationFailed:
		raise
	except Exception as _user_ex:
		# If we get here, we are unlikely to be able to print details from the
		# exception; the transaction will have already terminated, and
		# any __traceback_info__ objects or even the arguments to the
		# exception are possible invalid Persistent objects. Hence the need to
		# print it up there.
		result = _user_function_failed
		try:
			_user_ex_str = str(_user_ex)
			_user_ex_repr = str(_user_ex_repr)
		except:
			pass

	if result is _user_function_failed:
		if as_main:
			print("Failed to execute", getattr(fun, '__name__', fun), type(_user_ex),
				  _user_ex_str, _user_ex_repr)
			sys.exit(6)
		# returning none in this case is backwards compatibile behaviour. we'd really
		# like to raise...something
		result = None

	return result

import transaction

def _safe_close(conn):
	if conn is not None:
		try:
			conn.close()
		except StandardError:
			pass

def open_all_databases(db, close_children=False):
	conn = None
	try:
		with transaction.manager:
			conn = db.open()
			current = set(conn.connections.keys())
			for name in list(db.databases.keys()):
				if name not in current:
					child = conn.get_connection(name)
					if close_children:
						_safe_close(child)
	finally:
		_safe_close(conn)

@NoPickle
@interface.implementer(IDataserver)
class _MockDataserver(object):

	def __init__(self, dataserver_folder, root_connection):
		self.dataserver_folder = dataserver_folder
		self.root = dataserver_folder
		self.root_connection = root_connection
		self.users_folder = dataserver_folder['users']
		self.shards = dataserver_folder['shards']
		self.root_folder = dataserver_folder.__parent__

	def get_by_oid(self, *args, **kwargs):
		from nti.dataserver._Dataserver import get_by_oid
		return get_by_oid(*args, **kwargs)

import os
import os.path

def interactive_setup(root=".",
					  config_features=(),
					  xmlconfig_packages=(),
					  in_site=True,
					  with_dataserver=True,
					  with_library=False,
					  context=None):
	"""
	Set up the environment for interactive use, configuring the
	database and dataserver site. The root database ('Users')
	is returned.

	This should be done very early on in an interactive session.

	:keyword in_site: If ``True`` (the default), then the database
		will be opened and the ``nti.dataserver`` site will be made
		the current ZCA site. The return value will be
		(db, opened-connection, db-root)
	:keyword with_dataserver: If ``True`` (the default), an object presenting
		a minimal :class:`nti.dataserver.interfaces.IDataserver` interface
		will be registered globally.
	:keyword with_library: If ``True`` (*not* the default) then the library will
		be loaded from the ``etc/library.zcml`` file during the configuration process.
	"""

	log_format = '[%(name)s] %(levelname)s: %(message)s'
	logging.basicConfig(level=logging.INFO)
	logging.root.handlers[0].setFormatter(zope.exceptions.log.Formatter(log_format))

	setHooks()
	packages = ['nti.dataserver']
	if xmlconfig_packages:
		packages = set(xmlconfig_packages)
	context = _configure(set_up_packages=packages,
						 features=config_features,
						 context=context,
						 execute=False)
	if with_library:
		# XXX: Very similar to nti.appserver.application.
		DATASERVER_DIR = os.getenv('DATASERVER_DIR', '')
		dataserver_dir_exists = os.path.isdir(DATASERVER_DIR)
		if dataserver_dir_exists:
			DATASERVER_DIR = os.path.abspath(DATASERVER_DIR)
		def dataserver_file(*args):
			return os.path.join(DATASERVER_DIR, *args)
		def is_dataserver_file(*args):
			return dataserver_dir_exists and os.path.isfile(dataserver_file(*args))
		if is_dataserver_file('etc', 'library.zcml'):
			library_zcml = dataserver_file('etc', 'library.zcml')
			context = xmlconfig.file(library_zcml,
									 package=dottedname.resolve('nti.appserver'),
									 context=context,
									 execute=False)
	context.execute_actions()

	from nti.dataserver.config import temp_get_config
	env = temp_get_config(root)
	db = env.connect_databases()
	if not in_site:
		return db

	conn = db.open()
	root = conn.root()
	ds_folder = root['nti.dataserver']
	setSite(ds_folder)

	if with_dataserver:
		dataserver = _MockDataserver(ds_folder, conn)
		component.getGlobalSiteManager().registerUtility(dataserver)

	if with_library:
		try:
			from nti.contentlibrary.interfaces import IContentPackageLibrary
			component.getUtility(IContentPackageLibrary).syncContentPackages()
		except ImportError:
			logger.error("Library could not be loaded")

	return (db, conn, root)
