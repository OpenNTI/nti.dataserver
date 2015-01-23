#!/usr/bin/env python
"""
zope.generations generation 37 evolver for nti.dataserver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 37

import logging

from zope import component
from zope import interface
from zope.component.hooks import site, setHooks

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.oids import to_external_oid

@interface.implementer(nti_interfaces.IDataserver)
class MockDataserver(object):

	root = None
	def get_by_oid( self, oid_string, ignore_creator=False ):
		resolver = component.queryUtility( nti_interfaces.IOIDResolver )
		if resolver is None:
			logger.warn( "Using dataserver without a proper ISiteManager configuration." )
		return resolver.get_object_by_oid( oid_string, ignore_creator=ignore_creator ) if resolver else None

def migrate(userish, dataserver):

	if 'Everyone' in userish.friendsLists:
		everyone = userish.friendsLists['Everyone']
		if everyone.creator is None and len(everyone) <= 1: # old default Everyone had no creator and only the 'Everyone' community as a member
			logger.debug( 'Deleting ancient Everyone (%s) from %s', everyone.created, userish.username )
			del userish.friendsLists['Everyone']
			return everyone.created

def evolve( context ):
	"""
	Evolve 36 to 37 by looking for the (ancient and almost extinct) default 'Everyone'
	FriendsLists and removing it. Essentially no production accounts should actually
	have this as it was removed before production started.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	mock_ds = MockDataserver()
	mock_ds.root = ds_folder
	component.provideUtility( mock_ds, nti_interfaces.IDataserver )
	# Hush up the connection warnings from p_activate
	con_log = logging.getLogger('ZODB.Connection')
	con_log.setLevel( logging.FATAL )
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		users = ds_folder['users']
		bad_usernames = []
		good_usernames = []
		everyone_dates = []

		for username, user in users.items():
			try:
				user._p_activate()
			except KeyError: # pragma: no cover
				logger.debug( "Invalid user %s/%s. Shard not mounted?", username, to_external_oid( user ) )
				bad_usernames.append( (username, to_external_oid(user) ) )
				continue

			if nti_interfaces.IUser.providedBy( user ):
				good_usernames.append( username )
				created = migrate( user, mock_ds )
				if created:
					everyone_dates.append( created )

		logger.debug( "Found %s good users and %s bad users", good_usernames, bad_usernames )
		# Unfortunately, we won't be able to delete them without dropping down to private
		# data structures.
		#for username, _ in bad_usernames:
		#	del users[username]
		if everyone_dates:
			everyone_dates.sort()
			logger.debug( "Removed %s ancient Everyones (out of %s users); oldest from %s newest from %s",
						  len(everyone_dates), len(good_usernames) + len(bad_usernames),
						  everyone_dates[0], everyone_dates[-1] )


	con_log.setLevel( logging.NOTSET )
