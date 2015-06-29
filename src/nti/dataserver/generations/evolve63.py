#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 63

from zope import component
from zope import interface

from zope.component.hooks import site, setHooks

try:
	from nti.app.products.courseware.legacy_courses import KNOWN_LEGACY_COURSES_BY_SITE
except ImportError:
	KNOWN_LEGACY_COURSES_BY_SITE = {}

from nti.dataserver.users import Community
from nti.dataserver.users.interfaces import IDisallowMembershipOperations

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	dataserver_folder = root['nti.dataserver']

	with site(dataserver_folder):
		assert	component.getSiteManager() == dataserver_folder.getSiteManager(), \
				"Hooks not installed?"

		for site_courses in KNOWN_LEGACY_COURSES_BY_SITE.values():

			for value in site_courses or ():
				if len(value) < 4:
					continue
				
				scopes = value[2]
				for name in scopes.values():
					if not name:
						continue
					community = Community.get_community(name)
					if community is not None:
						interface.alsoProvides(community, IDisallowMembershipOperations)
					
	logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to 63 by marking old course comms.
	"""
	do_evolve(context)
