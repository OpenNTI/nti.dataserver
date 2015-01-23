#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 45

from zope import interface
from zope import component
from zope import lifecycleevent
from zope.component.hooks import site, setHooks

from zope.annotation.interfaces import IAnnotations
from zope.generations.utility import findObjectsProviding

from zope.dottedname import resolve as dottedname

from zc import intid as zc_intid

from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserver

from .install import install_metadata_catalog

@interface.implementer(IDataserver)
class MockDataserver(object):

	def __init__(self, dataserver_folder, root_connection):
		self.dataserver_folder = dataserver_folder
		self.root = dataserver_folder
		self.root_connection = root_connection
		self.users_folder = dataserver_folder['users']
		self.shards = dataserver_folder['shards']
		self.root_folder = dataserver_folder.__parent__

def evolve( context ):
	"""
	Evolve generation 44 to 45 by adding the general object metadata
	index.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	mock_ds = MockDataserver(ds_folder, context.connection)
	gsm = component.getGlobalSiteManager()
	gsm.registerUtility(mock_ds)

	# We have a very incestuous relationship with indexing
	# existing grades
	IGrade = dottedname.resolve('nti.app.products.gradebook.interfaces.IGrade')
	_store_grade_created_event = dottedname.resolve('nti.app.products.gradebook.subscribers._store_grade_created_event')

	try:
		with site( ds_folder ):
			logger.info( "Installing catalog" )

			# First, make the circled changes available.
			# See users.py
			# Then index grades; see nti.app.products.gradebook.subscribers
			for user in ds_folder['users'].values():
				for change in user.getContainedStream(''):
					if not change.object: # pragma: no cover
						continue

					# The ONLY things in the root stream are circled events
					user._circled_events_storage.append( change )
					change.__parent__ = user
					lifecycleevent.created( change )
					lifecycleevent.added( change )
					user._circled_events_intids_storage.add( change._ds_intid )

				_register_grades(user, IGrade, _store_grade_created_event)

			catalog = install_metadata_catalog( ds_folder, component.getUtility(zc_intid.IIntIds ) )
			catalog.updateIndexes(ignore_persistence_exceptions=True)

			logger.info( "Done installing catalog")
	finally:
		gsm.unregisterUtility(mock_ds)

def _register_grades(user, IGrade, _store_grade_created_event):
	if IGrade is None:
		return

	if not ICommunity.providedBy(user):
		return

	# We go directly through annotations so we're not dependent
	# on any site configuration where ICourseInstance, etc,
	# might be registered
	courses = IAnnotations(user).get('LegacyCourses')
	if not courses:
		return

	changes = [] # for testing we keep a list
	for course in courses.values():
		gradebook = IAnnotations(course).get('GradeBook')
		grades = findObjectsProviding(gradebook, IGrade)
		for grade in grades:
			change = _store_grade_created_event(grade, None)
			changes.append(change)

	return changes
