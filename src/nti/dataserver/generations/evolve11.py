#!/usr/bin/env python
"""zope.generations generation 11 evolver for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 11

from zope.generations.utility import findObjectsMatching
from zope import minmax

from nti.dataserver import sessions, interfaces as nti_interfaces
from nti.dataserver.chat_transcripts import _MeetingTranscriptStorage as MTS, _CopyingWeakRef as Ref

import ZODB.POSException
def _raises():
	raise ZODB.POSException.POSKeyError()

def evolve( context ):
	"""
	Evolve generation 10 to generation 11 by finding old chat transcripts and adding the right
	reference.
	"""
	for mts in findObjectsMatching( context.connection.root()['nti.dataserver'].getSiteManager(), lambda x: isinstance(x, MTS) ):
		mts._p_activate()
		if 'meeting' in mts.__dict__:
			try:
				ref = Ref( mts.__dict__['meeting'] )
				mts._meeting_ref = ref
			except KeyError:
				# Meeting gone
				mts._meeting_ref = _raises
			del mts.__dict__['meeting']

		try:
			for key in list(mts.messages.keys()):
				if not callable(mts.messages[key]):
					mts.messages[key] = Ref(mts.messages[key])
		except KeyError:
			# Meeting Gone.
			# Should never get here for real
			pass
