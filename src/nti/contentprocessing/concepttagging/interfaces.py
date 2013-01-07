from __future__ import print_function, unicode_literals

from zope import schema
from zope import interface
	
class IConceptSource(interface.Interface):
	"""
	represent a concept source entry (e.g. linked data) 
	"""
	source = schema.TextLine(title="source name", required=True)
	uri = schema.TextLine(title="source uri", required=True)
	
class IConcept(interface.Interface):
	"""
	represent a concept
	"""
	text = schema.TextLine(title="concept text", required=True)
	relevance = schema.Float(title="concept relevance", required=False)
	sources = schema.List(title="Concept sources", min_length=0, 
						  value_type=schema.Object(IConceptSource, title="The source" ) )
														
class IConceptTagger(interface.Interface):	
	
	def __call___(content):
		"""
		Return the IConcept(s) associated with the specified content
		
		:param content: Text to process
		"""
