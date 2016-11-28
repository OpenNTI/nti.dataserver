#!/usr/bin/env python
"""
zope.generations generation 36 evolver for nti.dataserver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 36

from zope import component
from zope import interface

from zope.component.hooks import site, setHooks

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.oids import to_external_oid

from nti.wref.interfaces import IWeakRef

@interface.implementer(nti_interfaces.IDataserver)
class MockDataserver(object):

	root = None
	def get_by_oid(self, oid_string, ignore_creator=False):
		resolver = component.queryUtility(nti_interfaces.IOIDResolver)
		if resolver is None:
			logger.warn("Using dataserver without a proper ISiteManager configuration.")
		return resolver.get_object_by_oid(oid_string, ignore_creator=ignore_creator) if resolver else None

def _check_bad(self, name, set_of_wref):
	bad = []
	for x in set_of_wref:
		if not hasattr(x, 'username'):
			bad.append(x())
	if bad:
		logger.debug("Bad %s weak references from user %s to %s", name, self, bad)
	return bad

def _rebuild_dynamic_member_ships(self):
	# Low-level rebuild of dynamic memberships because the set may have been corrupted
	self._p_activate()
	if '_dynamic_memberships' in self.__dict__:
		if not _check_bad(self, 'dynamic membership', self._dynamic_memberships):
			return

		all_memberships = list(self.dynamic_memberships)
		del self._dynamic_memberships
		for i in all_memberships:
			self._dynamic_memberships.add(IWeakRef(i))

def _rebuild_entities_followed(self):
	# Low-level rebuild of following because the set may have been corrupted
	self._p_activate()
	if '_entities_followed' in self.__dict__:
		if not _check_bad(self, 'entities followed', self._entities_followed):
			return
		all_memberships = list(self.entities_followed)
		del self._entities_followed
		for i in all_memberships:
			self._entities_followed.add(IWeakRef(i))

def migrate(userish, dataserver):

	dropped = set()
	retained = set()
	_rebuild_dynamic_member_ships(userish)
	_rebuild_entities_followed(userish)
	for relationship_name, exit_func in (('entities_followed', userish.stop_following),
										 ('dynamic_memberships', userish.record_no_longer_dynamic_member)):
		try:
			for x in list(getattr(userish, relationship_name)):
				try:
					if nti_interfaces.IFriendsList.providedBy(x) and userish not in x:
						exit_func(x)
						dropped.add(x)
					else:
						retained.add(x)
				except KeyError:  # pragma: no cover
					# a POSKeyError
					logger.debug("Error accessing one relationship %s for %s", 
								 relationship_name, userish)

		except KeyError:  # pragma: no cover
			# a POSKeyError
			logger.debug("Error accessing all relationship %s for %s",
						 relationship_name, userish)

	if dropped:
		logger.debug("User %s had these broken relationships: %s and these good ones: %s",
					 userish, dropped, retained)


def evolve(context):
	"""
	Evolve generation 35 to generation 36 by looking for bad
	`following` and `dynamic_membership` values.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	mock_ds = MockDataserver()
	mock_ds.root = ds_folder
	component.provideUtility(mock_ds, nti_interfaces.IDataserver)

	with site(ds_folder):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		users = ds_folder['users']
		bad_usernames = []
		good_usernames = []

		for username, user in users.items():
			try:
				user._p_activate()
			except KeyError:  # pragma: no cover
				logger.warn("Invalid user %s/%s. Shard not mounted?",
							 username, to_external_oid(user))
				bad_usernames.append((username, to_external_oid(user)))
				continue

			if nti_interfaces.IUser.providedBy(user):
				good_usernames.append(username)
				migrate(user, mock_ds)

		logger.debug("Found %s good users and %s bad users",
					 good_usernames, bad_usernames)

		# Unfortunately, we won't be able to delete them without dropping down to private
		# data structures.
		# for username, _ in bad_usernames:
		# 	del users[username]
