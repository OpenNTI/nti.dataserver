#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Concept tagging interfaces

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine

class IConceptSource(interface.Interface):
	"""
	represent a concept source entry (e.g. linked data) 
	"""
	source = ValidTextLine(title="source name", required=True)
	uri = ValidTextLine(title="source uri", required=True)

class IConcept(interface.Interface):
	"""
	represent a concept
	"""
	text = ValidTextLine(title="concept text", required=True)
	relevance = Number(title="concept relevance", required=False)
	sources = ListOrTuple(title="Concept sources", min_length=0,
						 			 value_type=Object(IConceptSource, title="The source"))

class IConceptTagger(interface.Interface):

	def __call___(content):
		"""
		Return the IConcept(s) associated with the specified content
		
		:param content: Text to process
		"""
