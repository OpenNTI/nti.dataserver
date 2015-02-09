#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenXerox lang detector

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import requests

from zope import interface

from . import Language

from .interfaces import ILanguageDetector

@interface.implementer(ILanguageDetector)
class _OpenXeroxLanguageDetector(object):

	url = u'https://services.open.xerox.com/RestOp/LanguageIdentifier/GetLanguageForString'

	def __call__(self, content, **kwargs):
		result = None
		headers = {u'content-type': u'application/x-www-form-urlencoded', 
				   u"Accept": "text/plain"}
		params = {u'document':unicode(content)}
		try:
			r = requests.post(self.url, data=params, headers=headers)
			data = r.json()
			if r.status_code == 200 and data:
				result = Language(code=data)
			else:
				logger.error("%s is an invalid status response code; %s",
							 r.status_code, data)
		except Exception:
			result = None
			logger.exception('Error while detecting language using OpenXerox')

		return result
