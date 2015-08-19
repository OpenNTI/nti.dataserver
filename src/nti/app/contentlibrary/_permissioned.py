#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import hashlib

from zope import component

from zope.component import hooks

from zope.traversing.interfaces import IEtcNamespace

from pyramid import security as psec

from nti.appserver.pyramid_authorization import is_readable

from nti.common.property import Lazy

from nti.dataserver.interfaces import IMemcacheClient
from nti.dataserver.interfaces import IAuthenticationPolicy

EXP_TIME = 1800

def _memcache_client():
	return component.queryUtility(IMemcacheClient)

def _last_synchronized():
	hostsites = component.queryUtility(IEtcNamespace, name='hostsites')
	result = getattr(hostsites, 'lastSynchronized', 0)
	return result

def _base_key(content_package, lastSync=None):
	result = hashlib.md5()
	cur_site = hooks.getSite()
	lastSync = _last_synchronized() if not lastSync else lastSync
	for value in ('pcpl', cur_site.__name__, content_package.ntiid, lastSync):
		result.update(str(value).lower())
	return result

def _effective_principals(request):
	result = (psec.Everyone,)
	authn_policy = component.queryUtility(IAuthenticationPolicy)
	if authn_policy is not None and request is not None:
		result = authn_policy.effective_principals(request)
	result = {getattr(x, 'id', str(x)).lower() for x in result}
	return sorted(result)

class _PermissionedContentPackageMixin(object):

	@Lazy
	def _client(self):
		return _memcache_client()

	def _test_and_cache(self, content_package):
		# test readability
		request = self.request
		if is_readable(content_package, request):
			result = True
		else:
			# Nope. What about a top-level child? TODO: Why we check children?
			result = any((is_readable(x, request) for x in content_package.children))

		try:
			# cache if possible
			client = self._client
			if client != None:
				lastSync = _last_synchronized()
				for name in _effective_principals(request):
					base = _base_key(content_package, lastSync)
					base.update(name)
					name = base.hexdigest()
					client.set(name, bool(result), time=EXP_TIME)
		except Exception as e:
			logger.error("Cannot set value(s) in memcached %s", e)
		return result

	def _test_is_readable(self, content_package):
		try:
			client = self._client
			if client != None:
				request = self.request
				lastSync = _last_synchronized()
				for name in _effective_principals(request):
					base = _base_key(content_package, lastSync)
					base.update(name)
					name = base.hexdigest()
					result = client.get(name)
					if result is not None:
						return result
		except Exception as e:
			logger.error("Cannot get value(s) in memcached %s", e)

		result = self._test_and_cache(content_package)
		return result
