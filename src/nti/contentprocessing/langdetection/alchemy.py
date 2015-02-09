#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Alchemy lang detector

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import requests
from cStringIO import StringIO

from zope import interface

from nti.common.property import alias

from nti.externalization.representation import WithRepr

from nti.schema.fieldproperty import createDirectFieldProperties

from ..utils import getAlchemyAPIKey

from . import Language

from .interfaces import IAlchemyLanguage
from .interfaces import ILanguageDetector

ALCHEMYAPI_LIMIT_KB = 150
ALCHEMYAPI_URL = u'http://access.alchemyapi.com/calls/text/TextGetLanguage'

@WithRepr
@interface.implementer(IAlchemyLanguage)
class _AlchemyLanguage(Language):
	createDirectFieldProperties(IAlchemyLanguage)
	code = alias('ISO_639_1')

	def __str__(self):
		return self.code

@interface.implementer(ILanguageDetector)
class _AlchemyTextLanguageDetector(object):

	__slots__ = ()

	def __call__(self, content, keyname=None, **kwargs):
		result = None
		content = content or u''
		size_kb = sys.getsizeof(content) / 1024.0
		if not content:
			result = None
		elif size_kb > ALCHEMYAPI_LIMIT_KB:
			s = StringIO(content)
			content = s.read(ALCHEMYAPI_LIMIT_KB)

		try:
			result = get_language(content, name=keyname, **kwargs) \
					 if content else None
		except:
			result = None
			logger.exception('Error while detecting language using Alchemy')

		return result

def get_language(content, name=None, **kwargs):
	apikey = getAlchemyAPIKey(name=name)
	headers = {u'content-type': u'application/x-www-form-urlencoded'}
	params = {u'text':unicode(content), u'apikey':apikey.value,
			  u'outputMode':u'json'}
	params.update(kwargs)

	r = requests.post(ALCHEMYAPI_URL, data=params, headers=headers)
	data = r.json()
	if r.status_code == 200 and data.get('status', 'ERROR') == 'OK':
		result = _AlchemyLanguage(ISO_639_1=data.get('iso-639-1'),
								  ISO_639_2=data.get('iso-639-2', None),
								  ISO_639_3=data.get('iso-639-3', None),
								  name=data.get('language', None))
	else:
		result = None
		logger.error('Invalid request status while detecting language; %s',
				 	 data.get('status', ''))

	return result
