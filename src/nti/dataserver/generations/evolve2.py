#!/usr/bin/env python
"""zope.generations generation 2 evolver for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 2

from zope.generations.utility import findObjectsMatching
from nti.dataserver.contenttypes import Highlight
from nti.dataserver import interfaces as nti_interfaces

def evolve( context ):
	"""
	Evolve generation 1 to generation 2 by changing all notes to be instance-backed.
	"""
	# Notes extend highlights, so in theory order matters (if we're treating some
	# fields specially). However, here we're simply copying everything over.
	# Now, we have an INote interface and could use 'findObjectsProviding', but
	# we never enforced an IHighlight interface, so we must rely on the class structure
	for old_note in findObjectsMatching( context.connection.root(), lambda x: isinstance(x,Highlight) ):
		if hasattr( old_note, 'data' ):
			# The old dictionary-based note structure
			for k in old_note.data:
				# Blacklist a few fields
				if k in ('Last Modified', 'CreatedTime'): continue
				# Transfer the rest
				setattr( old_note, k, old_note.data[k] )

			# Remove the evidence
			delattr( old_note, 'data' )
