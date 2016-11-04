#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 57

from zope import component
from zope.component.hooks import site, setHooks

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.library import _register_content_units

from nti.site.hostpolicy import run_job_in_all_host_sites

def _do_register_units():
	library = component.queryUtility(IContentPackageLibrary)
	if library is not None:
		logger.info('Registering units for %s', library)
		for package in library.contentPackages:
			_register_content_units( library, package)

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		assert	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		# We need to sync the global library first, or we'll
		# drop these top-level courses on the floor if
		# we find them within the site.  Unfortunately,
		# this errs out due to it not being able to find
		# the IDataserver utility. Perhaps because we're not
		# fully started at this point.

		run_job_in_all_host_sites(_do_register_units)

		# As a workaround, we could reset out top level library so
		# that everything will be picked up fresh as the ds starts.
		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Make sure all persistent content units are registered; this
	is primarily for caching/weak-ref usage.
	"""
	do_evolve(context)
