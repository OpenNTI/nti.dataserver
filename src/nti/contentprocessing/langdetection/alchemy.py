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

from zope import component
from zope import interface

from nti.utils.property import alias
from nti.utils.schema import createDirectFieldProperties

from . import Language
from . import interfaces as ld_interfaces
from .. import interfaces as cp_interfaces

@interface.implementer(ld_interfaces.IAlchemyLanguage)
class _AlchemyLanguage(Language):
	createDirectFieldProperties(ld_interfaces.IAlchemyLanguage)
	code = alias('ISO_639_1')

	def __repr__(self):
		return "%s(%s,%s,%s,%s)" % (self.__class__.__name__, self.name,
									self.ISO_639_1, self.ISO_639_2, self.ISO_639_3)

@interface.implementer(ld_interfaces.ILanguageDetector)
class _AlchemyTextLanguageDetector(object):

	limit_kb = 150
	url = u'http://access.alchemyapi.com/calls/text/TextGetLanguage'

	def __call__(self, content, keyname, **kwargs):
		result = None
		content = content or u''
		size_kb = sys.getsizeof(content) / 1024.0
		if not content:
			return result
		elif size_kb > self.limit_kb:
			s = StringIO(content)
			content = s.read(self.limit_kb)

		apikey = component.getUtility(cp_interfaces.IAlchemyAPIKey, name=keyname)
		headers = {u'content-type': u'application/x-www-form-urlencoded'}
		params = {u'text':unicode(content), u'apikey':apikey.value,
				  u'outputMode':u'json'}
		params.update(kwargs)
		try:
			r = requests.post(self.url, data=params, headers=headers)
			data = r.json()
			if r.status_code == 200 and data.get('status', 'ERROR') == 'OK':
				result = _AlchemyLanguage(ISO_639_1=data.get('iso-639-1'),
										  ISO_639_2=data.get('iso-639-2', None),
										  ISO_639_3=data.get('iso-639-3', None),
										  name=data.get('language', None))
		except Exception:
			result = None
			logger.exception('Error while detecting language using Alchemy')

		return result
