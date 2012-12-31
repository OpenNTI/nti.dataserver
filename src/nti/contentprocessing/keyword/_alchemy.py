from __future__ import print_function, unicode_literals

import requests

from zope import interface

from nti.contentprocessing.keyword import ContentKeyWord
from nti.contentprocessing.keyword import interfaces as cpkw_interfaces

import logging
logger = logging.getLogger( __name__ )

@interface.implementer( cpkw_interfaces.IKeyWordExtractor )
class _AlchemyAPIKeyWorExtractor():
	
	#TODO: Get NT API Key
	apikey = u'afe98c5b8fb8586e930d1b2128386d40c136e6d3'
	url = u'http://access.alchemyapi.com/calls/text/TextGetRankedKeywords'
	
	def __call__(self, content, **kwargs):
		headers = {u'content-type': u'application/x-www-form-urlencoded'}
		params = {u'text':unicode(content), u'apikey':self.apikey, u'outputMode':u'json'}
		params.update(kwargs)
		r = requests.post(self.url, params=params, headers=headers)
		data = r.json
		
		if r.status_code ==200 and data.get('status','ERROR') == 'OK':
			keywords = data.get('keywords', ())
			result = [ContentKeyWord(d['text'], float(d.get('relevance', 0))) for d in keywords]
		else:
			result = ()
				
		return result
