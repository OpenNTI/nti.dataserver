# -*- coding: utf-8 -*-
"""
Alchemy concept tagging

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import requests

from zope import component
from zope import interface

from ._concept import Concept
from ._concept import ConceptSource
from .. import interfaces as cp_interfaces
from . import interfaces as cpct_interfaces

@interface.implementer(cpct_interfaces.IConceptTagger)
class _AlchemyAPIKConceptTaggger(object):
	
	url = u'http://access.alchemyapi.com/calls/text/TextGetRankedConcepts'
	limit_kb = 150
		
	def __call__(self, content, keyname, **kwargs):
		result = ()	
		content = content or u''
		size_kb = sys.getsizeof(content)/1024.0
		if size_kb <= self.limit_kb:
			apikey = component.getUtility(cp_interfaces.IAlchemyAPIKey, name=keyname)
			headers = {u'content-type': u'application/x-www-form-urlencoded'}
			params = {u'text':unicode(content), u'apikey':apikey.value, u'outputMode':u'json'}
			params.update(kwargs)
			try:
				r = requests.post(self.url, params=params, headers=headers)
				data = r.json()
				
				if r.status_code == 200 and data.get('status','ERROR') == 'OK':
					result = []
					for entry in data.get('concepts', ()):
						sources = []
						text = relevance = None
						for k,v in entry.items():
							if k not in ('text', 'relevance'):
								sources.append(ConceptSource(k,v))
							elif k == 'text':
								text = v
							elif v is not None:
								relevance = float(v)
						result.append(Concept(text, relevance, sources))
			except:
				result = ()
				logger.exception('Error while getting concept tags from Alchemy')
							
		return result
