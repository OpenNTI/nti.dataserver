#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Administration views.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
from six import string_types

from zope import component

from zope.security.management import endInteraction
from zope.security.management import restoreInteraction

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.internalization import read_body_as_external_object
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.common.property import Lazy
from nti.common.string import TRUE_VALUES
from nti.common.maps import CaseInsensitiveDict

from nti.dataserver.interfaces import IRedisClient
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.authorization import ACT_SYNC_LIBRARY

from nti.externalization.interfaces import LocatedExternalDict

from .synchronize import synchronize

@view_config(permission=ACT_SYNC_LIBRARY)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context=IDataserverFolder,
			   name='SyncAllLibraries')
class _SyncAllLibrariesView(AbstractAuthenticatedView,
							ModeledContentUploadRequestUtilsMixin):
	"""
	A view that synchronizes all of the in-database libraries
	(and sites) with their on-disk and site configurations.
	If you GET this view, changes to not take effect but are just
	logged.

	.. note:: TODO: While this may be useful for scripts,
		we also need to write a pretty HTML page that shows
		the various sync stats, like time last sync'd, whether
		the directory is found, etc, and lets people sync
		from there.
	"""

	# Because we'll be doing a lot of filesystem IO, which may not
	# be well cooperatively tasked (gevent), we would like to give
	# the opportunity for other greenlets to run by sleeping inbetween
	# syncing each library. However, for some reason, under unittests,
	# this leads to very odd and unexpected test failures
	# (specifically in nti.app.products.courseware) so we allow
	# disabling it.
	_SLEEP = True

	# The amount of time for which we will hold the lock during
	# sync
	lock_timeout = 60 * 30  # 30 minutes

	lock_name = '/var/libraries/Lock/sync'

	def readInput(self, value=None):
		result = CaseInsensitiveDict()
		if self.request:
			if self.request.body:
				values = read_body_as_external_object(self.request)
			else:
				values = self.request.params
			result.update(values)
		return result

	@Lazy
	def redis(self):
		return component.getUtility(IRedisClient)

	@Lazy
	def lock(self):
		return self.redis.lock(self.lock_name, self.lock_timeout)

	def _do_call(self):
		values = self.readInput()
		site = values.get('site')
		allowRemoval = values.get('allowRemoval') or u''
		allowRemoval = allowRemoval.lower() in TRUE_VALUES
		packages = values.get('packages') or values.get('package') or ()
		packages = set(packages.split()) if isinstance(packages, string_types) else packages
		# Unfortunately, zope.dublincore includes a global subscriber registration
		# (zope.dublincore.creatorannotator.CreatorAnnotator)
		# that will update the `creators` property of IZopeDublinCore to include
		# the current principal when any ObjectCreated /or/ ObjectModified event
		# is fired, if there is a current interaction. Normally we want this,
		# but here we care specifically about getting the dublincore metadata
		# we specifically defined in the libraries, and not the requesting principal.
		# Our simple-minded approach is to simply void the interaction during this process
		# (which works so long as zope.securitypolicy doesn't get involved...)
		# This is somewhat difficult to test the side-effects of, sadly.
		now = time.time()
		result = LocatedExternalDict()
		result['Started'] = now
		endInteraction()
		try:
			params, results = synchronize(sleep=self._SLEEP,
										  site=site,
										  packages=packages,
										  allowRemoval=allowRemoval)
			result['Params'] = params
			result['Results'] = results
		finally:
			restoreInteraction()
			result['Elapsed'] = time.time() - now
		return result

	def __call__(self):
		with self.lock:
			return self._do_call()
