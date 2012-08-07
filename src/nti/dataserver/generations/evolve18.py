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


def evolve( context ):
	"""
	Evolve generation 17 to generation 18 by changing the root session storage.
	"""
	conn = context.connection

	sess_storage = session_storage.OwnerBasedAnnotationSessionServiceStorage()

	lsm = conn.root()['nti.dataserver'].getSiteManager()
	# This overwrites the previous definition, which at this point
	# is a broken object.
	lsm.registerUtility( sess_storage, provided=nti_interfaces.ISessionServiceStorage )

	# TODO: we probably need to add a step to drop all chat_transcript._IMeetingTranscriptStorage
	# again. Those are probably all full of broken objects now (once the Sessions database goes away),
	# and we need to clean up the intid storage from them
