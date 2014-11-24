#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 49 evolver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 49

from zope import component
from zope.component.hooks import site, setHooks

from .evolve45 import MockDataserver

def evolve( context ):
	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	mock_ds = MockDataserver(ds_folder, context.connection)
	gsm = component.getGlobalSiteManager()
	gsm.registerUtility(mock_ds)

	try:
		with site( ds_folder ):
			logger.info( "Updating enrollments" )

			from nti.app.products.courseware import legacy_courses
			legacy_courses._migrate_enrollments()
	finally:
		gsm.unregisterUtility(mock_ds)
