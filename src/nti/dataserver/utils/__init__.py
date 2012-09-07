#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import logging

import sys

from zope.exceptions.exceptionformatter import print_exception
import zope.exceptions.log
from zope import component
from zope import interface
from zope.dottedname import resolve as dottedname
from zope.component.hooks import setHooks
from zope.configuration import xmlconfig, config


from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver._Dataserver import Dataserver

def _configure(self=None, set_up_packages=(), features=(), context=None):

	# zope.component.globalregistry conveniently adds
	# a zope.testing.cleanup.CleanUp to reset the globalSiteManager
	if set_up_packages:
		if context is None:
			context = config.ConfigurationMachine()
			xmlconfig.registerCommonDirectives( context )
		for feature in features:
			context.provideFeature( feature )

		for i in set_up_packages:
			__traceback_info__ = (i, self, set_up_packages)
			if isinstance( i, tuple ):
				filename = i[0]
				package = i[1]
			else:
				filename = 'configure.zcml'
				package = i

			if isinstance( package, basestring ):
				package = dottedname.resolve( package )
			context = xmlconfig.file( filename, package=package, context=context )

		return context


def run_with_dataserver( environment_dir=None, function=None,
						 as_main=True, verbose=False,
						 config_features=(), xmlconfig_packages=() ):
	"""
	Execute the `function` in the (already running) dataserver
	environment configured at `environment_dir`.

	:keyword string environment_dir: The filesystem path to a dataserver environment.
	:keyword function function: The function of no parameters to execute.
	:keyword bool as_main: If ``True`` (the default) assumes this is the main portion
		of a script and configures the complete environment appropriately, including
		setting up logging.
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


	def user_fun():
		"""Run the user-given function in the environment; print exceptions
		in this env too."""
		try:
			function()
		except Exception:
			print_exception( *sys.exc_info() )
			raise

	def fun():
		ds = Dataserver( environment_dir )
		component.provideUtility( ds , nti_interfaces.IDataserver)

		try:
			return component.getUtility( nti_interfaces.IDataserverTransactionRunner )( user_fun )
		except Exception:
			pass
		finally:
			component.getSiteManager().unregisterUtility( ds, nti_interfaces.IDataserver )

	return run( function=fun, as_main=as_main, verbose=verbose,
				config_features=config_features,
				xmlconfig_packages=xmlconfig_packages, _print_exc=False )

def run( function=None, as_main=True, verbose=False, config_features=(), xmlconfig_packages=(), _print_exc=True ):
	"""
	Execute the `function`, taking care to print exceptions and handle configuration.

	:keyword function function: The function of no parameters to execute.
	:keyword bool as_main: If ``True`` (the default) assumes this is the main portion
		of a script and configures the complete environment appropriately, including
		setting up logging.
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
		logging.basicConfig(level=logging.WARN if not verbose else logging.INFO)
		logging.root.handlers[0].setFormatter( zope.exceptions.log.Formatter( '[%(name)s] %(levelname)s: %(message)s' ) )

		setHooks()
		packages = ['nti.dataserver']
		packages.extend( xmlconfig_packages )
		try:
			_configure( set_up_packages=packages, features=config_features )
		except Exception:
			print_exception( *sys.exc_info() )
			sys.exit( 5 )


	if _print_exc:
		def fun():
			"""Run the user-given function in the environment; print exceptions
			in this env too."""
			try:
				function()
			except Exception:
				print_exception( *sys.exc_info() )
				raise
	else:
		fun = function

	try:
		return fun()
	except Exception:
		pass
