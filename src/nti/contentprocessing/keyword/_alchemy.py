from __future__ import print_function, unicode_literals

from zope import interface

from nti.contentprocessing.keyword import interfaces as cpkw_interfaces

@interface.implementer( cpkw_interfaces.IKeyWordExtractor )
class _AlchemyAPIKeyWorExtractor():
	
	#TODO: Get NT API Key
	apikey = u'afe98c5b8fb8586e930d1b2128386d40c136e6d3'
	
	def __call__(self, content):
		pass

