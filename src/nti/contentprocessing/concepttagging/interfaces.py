# -*- coding: utf-8 -*-
"""
Concept tagging interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from nti.utils import schema as nti_schema

class IConceptSource(interface.Interface):
	"""
	represent a concept source entry (e.g. linked data) 
	"""
	source = nti_schema.ValidTextLine(title="source name", required=True)
	uri = nti_schema.ValidTextLine(title="source uri", required=True)

class IConcept(interface.Interface):
	"""
	represent a concept
	"""
	text = nti_schema.ValidTextLine(title="concept text", required=True)
	relevance = nti_schema.Number(title="concept relevance", required=False)
	sources = schema.List(title="Concept sources", min_length=0,
						  value_type=schema.Object(IConceptSource, title="The source"))

class IConceptTagger(interface.Interface):

	def __call___(content):
		"""
		Return the IConcept(s) associated with the specified content
		
		:param content: Text to process
		"""
