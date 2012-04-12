#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import logging

from zope import component
from zope.component.hooks import setHooks
from zope.configuration import xmlconfig

import nti.dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver._Dataserver import Dataserver

def run_with_dataserver( environment_dir=None, function=None, as_main=True ):
	"""
	Execute the `function` in the (already running) dataserver
	environment configured at `environment_dir`.

	:keyword string environment_dir: The filesystem path to a dataserver environment.
	:keyword function function: The function of no parameters to execute.
	:keyword bool as_main: If ``True`` (the default) assumes this is the main portion
		of a script and configures the complete environment appropriately, including
		setting up logging.

	:return: The results of the function
	"""

	if as_main:
		logging.basicConfig(level=logging.WARN)
		setHooks()
		xmlconfig.file( 'configure.zcml', package=nti.dataserver )

	ds = Dataserver( environment_dir )
	component.provideUtility( ds )
	try:
		return component.getUtility( nti_interfaces.IDataserverTransactionRunner )( function )
	finally:
		component.getSiteManager().unregisterUtility( ds )
