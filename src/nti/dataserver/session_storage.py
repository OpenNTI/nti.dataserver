#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Storage for sessions, providing an implementation of :class:`nti.dataserver.interfaces.ISessionServiceStorage`

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.annotation import IAnnotations

import persistent
import BTrees

from nti.utils.sets import discard

from nti.dataserver import users
from nti.dataserver import intid_utility
from nti.dataserver import interfaces as nti_interfaces

_OWNED_SESSIONS_KEY = __name__ + '.' + '_OwnerAnnotationBasedServiceStorage' + '.' + 'session_set'

def _session_id_set_for_session_owner( session_owner, family, default=None ):
	"""
	:param dict default: If not none, this will be used as the :class:`IAnnotations` value
		if the session's owner cannot be found or adapted to annotations.
	"""
	__traceback_info__ = session_owner, default
	user = users.User.get_user( session_owner )
	annotations = IAnnotations( user ) if default is None else IAnnotations( user, default )
	try:
		session_set = annotations[_OWNED_SESSIONS_KEY]
	except KeyError:
		session_set = annotations.setdefault( _OWNED_SESSIONS_KEY, family.II.TreeSet() )

	return session_set

@interface.implementer(nti_interfaces.ISessionServiceStorage)
class OwnerBasedAnnotationSessionServiceStorage(persistent.Persistent):
	"""
	Stores sessions on the owner using annotations. Keeps an index
	of the sessions using an intid utility we keep private to us
	(so as not to overwhelm the main intid utilities). (TODO: Is that
	wise/necessary?)
	TODO: Given the current policy (see chatserver), we can probably
	really go down to only keeping one active session per user.
	"""

	family = BTrees.family64

	def __init__( self, family=None ):
		if family: # pragma: no cover
			self.family = family
		# TODO: Use the same or different attribute name as the main
		# intid utility? The 'id' attribute has to be an ascii string,
		# so we can't directly use that...since we cannot look them
		# up in the same utility, it seems to make sense to use different
		# attributes
		intids = intid_utility.IntIds('_session_intid', family=self.family )
		intids.__name__ = '++etc++session_intids'
		intids.__parent__ = self

		self.intids = intids

	def register_session( self, session ):
		session_id = self.intids.register( session )
		session.id = hex(session_id).encode( 'ascii' )
		logger.info( 'Created session id %s', session.id )
		_session_id_set_for_session_owner( session.owner, self.family ).add( session_id )

	def get_session( self, session_id ):
		# The session id is supposed to come in as the base 16 session id we created
		# in register_session
		try:
			session_id = int( session_id, 0 )
		except TypeError: # pragma: no cover
			# probably already an int
			pass
		try:
			return self.intids.queryObject( session_id )
		except TypeError: # pragma: no cover
			# We couldn't convert the session_id to an int
			pass

	def get_sessions_by_owner( self, session_owner ):
		session_ids = _session_id_set_for_session_owner( session_owner, self.family, default={} )
		for sid in session_ids:
			session = self.intids.getObject( sid ) # If the object doesn't exist, we have an inconsistency!
			yield session

	def unregister_session( self, session ):
		session_id = self.intids.queryId( session )
		if session_id is None:
			# Not registered, or gone
			return

		discard( _session_id_set_for_session_owner( session.owner, self.family ),
				 session_id )
		self.intids.unregister( session )
