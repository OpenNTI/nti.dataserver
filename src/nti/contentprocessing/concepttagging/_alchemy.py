from __future__ import print_function, unicode_literals

import sys
import requests

from zope import component
from zope import interface

from nti.contentprocessing import interfaces as cp_interfaces
from nti.contentprocessing.concepttagging import interfaces as cpct_interfaces

import logging
logger = logging.getLogger( __name__ )

@interface.implementer( cpct_interfaces.IConceptTagger )
class _AlchemyAPIKConceptTaggger():
	
	url = u'http://access.alchemyapi.com/calls/text/TextGetRankedConcepts'
	limit_kb = 150
	
	@property
	def apikey(self):
		return component.getUtility(cp_interfaces.IAlchemyAPIKey)
		
	def __call__(self, content, **kwargs):
		result = ()	
		content = content or u''
		size_kb = sys.getsizeof(content)/1024.0
		if size_kb <= self.limit_kb:
			headers = {u'content-type': u'application/x-www-form-urlencoded'}
			params = {u'text':unicode(content), u'apikey':self.apikey, u'outputMode':u'json'}
			params.update(kwargs)
			try:
				r = requests.post(self.url, params=params, headers=headers)
				data = r.json
				
				if r.status_code ==200 and data.get('status','ERROR') == 'OK':
					import pprint
					pprint.pprint(data)
			except:
				result = ()
				logger.exception('Error while getting concept tags from Alchemy')
							
		return result
