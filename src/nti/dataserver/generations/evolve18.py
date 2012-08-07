#!/usr/bin/env python
"""
zope.generations generation 18 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 18

from nti.dataserver import session_storage
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.chat_transcripts import _DocidMeetingTranscriptStorage, _IMeetingTranscriptStorage

import zc.intid


def evolve( context ):
	"""
	Evolve generation 17 to generation 18 by changing the root session storage,
	and removing access to broken message objects.
	"""
	conn = context.connection

	sess_storage = session_storage.OwnerBasedAnnotationSessionServiceStorage()

	lsm = conn.root()['nti.dataserver'].getSiteManager()
	# This overwrites the previous definition, which at this point
	# is a broken object.
	lsm.registerUtility( sess_storage, provided=nti_interfaces.ISessionServiceStorage )

	# Now drop all chat_transcript._IMeetingTranscriptStorage
	# Those are probably all full of broken objects now (once the Sessions database goes away),
	# and we need to clean up the intid storage from them
	# TODO: This should probably force a user re-index

	dataserver_folder = conn.root()['nti.dataserver']

	intids = lsm.queryUtility( zc.intid.IIntIds )

	for type_ in ('users', 'providers'):
		for user in dataserver_folder[type_].values():
			__traceback_info__ = type_, user

			to_drop = []
			for container in user.containers.values() if hasattr(user, 'containers') else (): # 3. (idempotent)
				for obj in container.values():
					__traceback_info__ = type_, user, container, obj
					if isinstance( obj, float ): #pragma: no cover
						pass
					elif _IMeetingTranscriptStorage.providedBy( obj ):
						to_drop.append( obj )


			for obj in to_drop:
				try:
					user.deleteContainedObject( obj.containerId, obj.id )
				except: # pragma: no cover
					pass # if it was IBroken, we probably cannot actually do this

				if isinstance( obj, _DocidMeetingTranscriptStorage ):
					messages = getattr( obj, 'messages', () )
					# These messages will all be in the Session database, which we
					# no longer access. Forcibly unregister
					for intid in messages:
						intids.refs.pop( intid, None )
