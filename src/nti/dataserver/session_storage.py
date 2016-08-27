#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Storage for sessions, providing an implementation of
:class:`nti.dataserver.interfaces.ISessionServiceStorage`

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.keyreference.interfaces import NotYet
from zope.keyreference.interfaces import IKeyReference

from zope.lifecycleevent import IObjectRemovedEvent

from ZODB.interfaces import IConnection

from ZODB.POSException import POSKeyError

import BTrees

import persistent

from nti.common.sets import discard

from nti.dataserver import users

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ISessionServiceStorage

from nti.intid import utility as intid_utility

from nti.property.property import Lazy

from nti.zodb import readCurrent

# Leaving this key around for historical purposes:
# We used to use this as an annotation key on users that held
# an LLTreeSet to hold session_ids. But that was a duplicate
# of what we're already doing in the intids `refs` btree
# When we switched, we didn't delete annotations
_OWNED_SESSIONS_KEY = __name__ + '.' + '_OwnerAnnotationBasedServiceStorage' + '.' + 'session_set'

def _read_current(obj, container=False):
	return readCurrent(obj, container=container)

def _u(o):
	return getattr(o, 'username', o)

class _OwnerSetMapping(persistent.Persistent):

	__name__ = None
	__parent__ = None

	family = BTrees.family64

	def __init__(self, family=None):
		if family:
			self.family = family
		self._by_owner = self.family.OO.BTree()

	def set_for_owner(self, username, create=True, current=True):
		username = _u(username)
		if current:
			_read_current(self._by_owner)
		try:
			result = self._by_owner[username]
			if current:
				_read_current(result)
		except KeyError:
			if create:
				result = self._by_owner[username] = self.family.OO.Set()
			else:
				result = ()
		return result

	def add_session(self, session):
		for_owner = self.set_for_owner(session.owner, current=False)
		try:
			ref = IKeyReference(session)
		except NotYet:
			# ok, can we find an owner user? Fallback is us
			# TODO Why are we doing this?
			user = users.User.get_user(session.owner)
			for o in user, self:
				try:
					IConnection(o, None).add(session)
					break
				except AttributeError:
					pass
			ref = IKeyReference(session)
		for_owner.add(ref)

	def drop_session(self, session):
		for_owner = self.set_for_owner(session.owner)
		try:
			ref = IKeyReference(session)
		except NotYet:
			# Could never have had it
			pass
		else:
			discard(for_owner, ref)

	def drop_all_sessions_for_owner(self, session_owner):
		session_owner = _u(session_owner)
		try:
			del self._by_owner[session_owner]
		except KeyError:
			pass

	def sessions_for_owner(self, session_owner):
		for_owner = self.set_for_owner(session_owner,
									   create=False,
									   current=False)

		for ref in tuple(for_owner):
			result = ref()
			try:
				_read_current(result)
			except POSKeyError:
				# We've seen cases (alpha, prod) where
				# sessions are in our structure, but not in the db.
				# This may have something to do with partial (?)
				# commits between multiple dbs that may occur
				# during ds shutdown. We clean those up here.
				discard(for_owner, ref)
				continue
			yield result

@interface.implementer(ISessionServiceStorage)
class OwnerBasedAnnotationSessionServiceStorage(persistent.Persistent):
	"""
	A global utility to keep track of sessions. Keeps an index
	of the sessions using an intid utility we keep private to us
	(so as not to overwhelm the main intid utilities).
	"""

	family = BTrees.family64

	def __init__(self, family=None):
		if family:  # pragma: no cover
			self.family = family
		# TODO: Use the same or different attribute name as the main
		# intid utility? The 'id' attribute has to be an ascii string,
		# so we can't directly use that...since we cannot look them
		# up in the same utility, it seems to make sense to use different
		# attributes
		intids = intid_utility.IntIds('_session_intid', family=self.family)
		intids.__name__ = '++etc++session_intids'
		intids.__parent__ = self
		self.intids = intids

	@Lazy
	def _by_owner(self):
		self._p_changed = True

		by_owner = _OwnerSetMapping(self.family)
		by_owner.__parent__ = self
		by_owner.__name__ = '_by_owner'

		for session in self._intids_rc.refs.values():
			by_owner.add_session(session)
		return by_owner

	@property
	def _intids_rc(self):
		_read_current(self.intids)
		_read_current(self.intids.refs)
		return self.intids

	def register_session(self, session):
		session_id = self._intids_rc.register(session)
		session.id = hex(session_id)
		self._by_owner.add_session(session)
		logger.info('Registered session id %s for %s', session.id, session.owner)

	def get_session(self, session_id):
		# The session id is supposed to come in as the base 16 session id we created
		# in register_session
		try:
			session_id = int(session_id, 0)
		except TypeError:  # pragma: no cover
			# probably already an int
			pass
		try:
			return self.intids.queryObject(session_id)
		except TypeError:  # pragma: no cover
			# We couldn't convert the session_id to an int
			pass

	def get_sessions_by_owner(self, session_owner):
		return self._by_owner.sessions_for_owner(session_owner)

	def unregister_session(self, session):
		if session is None:
			return
		session_id = self._intids_rc.queryId(session)
		if session_id is not None:
			# Not registered, or gone
			self.intids.unregister(session)

		self._by_owner.drop_session(session)
		logger.info("Unregistered session %s for %s", session_id, session.owner)

	def unregister_all_sessions_for_owner(self, session_owner):
		for session in list(self._by_owner.sessions_for_owner(session_owner)):
			self.unregister_session(session)

		self._by_owner.drop_all_sessions_for_owner(session_owner)
		logger.info("Unregistered all sessions for %s", session_owner)

@component.adapter(IUser, IObjectRemovedEvent)
def _remove_sessions_for_removed_user(user, event):
	storage = component.queryUtility(ISessionServiceStorage)
	# This is tightly coupled to OwnerBasedAnnotationSessionServiceStorage
	if hasattr(storage, 'unregister_all_sessions_for_owner'):
		try:
			storage.unregister_all_sessions_for_owner(user)
		except Exception:
			# The consequence might be some extra storage space used
			# but nothing dire
			logger.exception("Failed to remove all sessions for %s", user)
