from __future__ import print_function, unicode_literals

from zope import interface
					
class IConceptTagger(interface.Interface):	
	
	def __call___(content):
		"""
		Return the concepts associated with the specified content
		
		:param content: Text to process
		"""
