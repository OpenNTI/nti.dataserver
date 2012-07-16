#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NTIID related interfaces.


$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import schema
from zope.interface.common import sequence
from dolmen.builtins import ITuple

class INTIID(ITuple,sequence.IMinimalSequence):
	"""
	Represents the parts of an NTIID that has been parsed.

	In addition to the named fields, this object acts as a 4-tuple,
	(provider, type, specific, date)

	"""
	provider = schema.TextLine( title="The username of the creating/providing entity." )
	nttype = schema.TextLine( title="The type of the NTIID." )
	specific = schema.TextLine( title="The type-specific portion of the NTIID." )
	date = schema.TextLine( title="The date portion of the NTIID." )

class INTIIDResolver(interface.Interface):
	"""
	An object that can take an NTIID and produce the object
	to which it refers.

	These should be registered as components named for the ntiid type (e.g, OID).

	"""

	def resolve( ntiid_string ):
		"""
		:return: The object to which the `ntiid_string` refers,
			or None if it cannot be found.
		"""
