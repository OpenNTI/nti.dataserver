#!/usr/bin/env python
"""
zope.generations generation 35 evolver for nti.dataserver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 35

from zope import component
from zope import interface
from zope.component.hooks import site, setHooks

from nti.dataserver import users
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.externalization.oids import to_external_oid

from nti.wref.interfaces import IWeakRef

@interface.implementer(IDataserver)
class MockDataserver(object):

	root = None
	def get_by_oid( self, oid_string, ignore_creator=False ):
		resolver = component.queryUtility(IOIDResolver )
		if resolver is None:
			logger.warn( "Using dataserver without a proper ISiteManager configuration." )
		return resolver.get_object_by_oid( oid_string, ignore_creator=ignore_creator ) if resolver else None



def migrate(userish, dataserver):
	# First, the entity references
	for old_key, new_key in ( ('_sources_not_accepted', '_entities_not_accepted'),
							  ('_sources_accepted', '_entities_accepted'),
							  ('_communities', '_dynamic_memberships'),
							  ('_following', '_entities_followed'),
							  ):

		old_value = getattr( userish, old_key, dataserver )
		if old_value is dataserver:
			continue
		delattr( userish, old_key )
		if len(old_value) == 0:
			#logger.info( "No need to migrate %s for %s", old_key, userish )
			continue # don't create the new one

		#logger.info( "Migrating %s %s to %s", userish, old_key, new_key )
		new_value = getattr( userish, new_key ) # auto-create
		for username in old_value:
			entity = userish.get_entity( username, dataserver=dataserver, default=old_value )
			if entity is old_value:
				entity = users.Entity.get_entity( username, dataserver=dataserver, default=old_value )

			if entity is old_value:
				entity = None

			if entity:
				try:
					entity._p_activate()
				except KeyError:
					entity = None

			if entity:
				new_value.add( IWeakRef( entity ) )
			else:
				logger.debug( "Unable to find %s for %s in %s", username, userish, old_key )

	if hasattr( userish, 'muted_oids' ):
		old_value = getattr( userish, 'muted_oids' )
		delattr( userish, 'muted_oids' )
		userish.__dict__['_muted_oids'] = old_value


def evolve( context ):
	"""
	Evolve generation 34 to generation 35 by replacing all outstanding
	username references with weak refs.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	mock_ds = MockDataserver()
	mock_ds.root = ds_folder
	component.provideUtility( mock_ds, IDataserver )

	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		users = ds_folder['users']
		bad_usernames = []
		good_usernames = []

		for username, user in users.items():
			try:
				user._p_activate()
			except KeyError:
				logger.warn( "Invalid user %s/%s. Shard not mounted? Refs may be lost", 
							username, to_external_oid( user ) )
				bad_usernames.append( (username, to_external_oid(user) ) )
				continue

			good_usernames.append( username )
			migrate( user, mock_ds )
			if hasattr( user, 'friendsLists' ):
				for fl in user.friendsLists.values():
					migrate( fl, mock_ds )

		logger.debug("Found %s good users and %s bad users", 
					 good_usernames, bad_usernames )
		# Unfortunately, we won't be able to delete them without dropping down to private
		# data structures.
		#for username, _ in bad_usernames:
		#	del users[username]

		for username, user in ds_folder.get('providers', {}).items():
			#user._p_activate()
			migrate( user, mock_ds )
