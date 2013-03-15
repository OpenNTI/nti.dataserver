# -*- coding: utf-8 -*-
"""
Alchemy keyword extractor

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import requests

from zope import component
from zope import interface
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.utils.property import alias
from nti.utils.schema import SchemaConfigured

from . import interfaces as ld_interfaces
from .. import interfaces as cp_interfaces

@interface.implementer(ld_interfaces.IAlchemyLanguage)
class _AlchemyLanguage(SchemaConfigured):

	ISO_639_1 = FP(ld_interfaces.IAlchemyLanguage['ISO_639_1'])
	ISO_639_2 = FP(ld_interfaces.IAlchemyLanguage['ISO_639_2'])
	ISO_639_3 = FP(ld_interfaces.IAlchemyLanguage['ISO_639_3'])
	name = FP(ld_interfaces.IAlchemyLanguage['name'])

	code = alias('ISO_639_1')

	def __str__(self):
		return self.code

	def __repr__(self):
		return "(%s,%s,%s,%s)" % (self.name, self.ISO_639_1, self.ISO_639_2, self.ISO_639_3)

	def __eq__(self, other):
		return self is other or (isinstance(other, _AlchemyLanguage)
 								 and self.code == other.code)

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.code)
		return xhash

@interface.implementer(ld_interfaces.ILanguageDetector)
class _AlchemyTextLanguageDectector(object):

	limit_kb = 150
	url = u'http://access.alchemyapi.com/calls/text/TextGetLanguage'

	def __call__(self, content, keyname, **kwargs):
		result = None
		content = content or u''
		size_kb = sys.getsizeof(content) / 1024.0
		if not content or size_kb > self.limit_kb:
			return result

		apikey = component.getUtility(cp_interfaces.IAlchemyAPIKey, name=keyname)
		headers = {u'content-type': u'application/x-www-form-urlencoded'}
		params = {u'text':unicode(content), u'apikey':apikey.value, u'outputMode':u'json'}
		params.update(kwargs)
		try:
			r = requests.post(self.url, params=params, headers=headers)
			data = r.json()
			if r.status_code == 200 and data.get('status', 'ERROR') == 'OK':
				result = _AlchemyLanguage(ISO_639_1=data.get('iso-639-1'),
										  ISO_639_2=data.get('iso-639-2', None),
										  ISO_639_3=data.get('iso-639-3', None),
										  name=data.get('language', None))
		except:
			result = ()
			logger.exception('Error while detecting language using Alchemy')

		return result
