#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alchemy concept tagging

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import requests

from zope import component
from zope import interface

from . import concept
from . import interfaces as cp_interfaces
from .. import interfaces as tagging_interfaces

ALCHEMYAPI_LIMIT_KB = 150
ALCHEMYAPI_URL = u'http://access.alchemyapi.com/calls/text/TextGetRankedConcepts'

def get_ranked_concepts(content, name=u'', **kwargs):
	apikey = component.getUtility(tagging_interfaces.IAlchemyAPIKey, name=name)
	headers = {u'content-type': u'application/x-www-form-urlencoded'}
	params = {u'text':unicode(content), u'apikey':apikey.value, u'outputMode':u'json'}
	params.update(kwargs)
			
	r = requests.post(ALCHEMYAPI_URL, params=params, headers=headers)
	data = r.json()

	if r.status_code == 200 and data.get('status', 'ERROR') == 'OK':
		result = []
		for entry in data.get('concepts', ()):
			sources = []
			text = relevance = None
			for k, v in entry.items():
				if k not in ('text', 'relevance'):
					sources.append(concept.ConceptSource(k, v))
				elif k == 'text':
					text = v
				elif v is not None:
					relevance = float(v)
			result.append(concept.Concept(text, relevance, sources))
	else:
		result = ()
		logger.error('Invalid request status while getting concept tags from Alchemy')
		
	return result

@interface.implementer(cp_interfaces.IConceptTagger)
class _AlchemyAPIKConceptTaggger(object):

	def __call__(self, content, keyname=u'', **kwargs):
		content = content or u''
		size_kb = sys.getsizeof(content) / 1024.0
		if not content or size_kb > ALCHEMYAPI_LIMIT_KB:
			return ()

		try:
			result = get_ranked_concepts(content, name=keyname, **kwargs)
		except:
			result = ()
			logger.exception('Error while getting concept tags from Alchemy')

		return result
