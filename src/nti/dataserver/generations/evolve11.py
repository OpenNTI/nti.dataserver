#!/usr/bin/env python
"""zope.generations generation 11 evolver for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 11

import ZODB.POSException
def _raises():
	raise ZODB.POSException.POSKeyError()

def evolve( context ):
	"""
	Evolve generation 10 to generation 11 by finding old chat transcripts and adding the right
	reference.

	This evolution is no longer supported and is a no-op.
	"""
