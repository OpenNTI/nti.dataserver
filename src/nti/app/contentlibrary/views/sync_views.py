#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Administration views.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import time
import traceback
from six import string_types

import transaction
try:
	from transaction._compat import get_thread_ident
except ImportError:
	def get_thread_ident():
		return id(transaction.get())

from zope import component

from zope.security.management import endInteraction
from zope.security.management import restoreInteraction

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error
from nti.app.externalization.internalization import read_body_as_external_object
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.common.property import Lazy
from nti.common.string import TRUE_VALUES
from nti.common.maps import CaseInsensitiveDict

from nti.dataserver.interfaces import IRedisClient
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.authorization import ACT_SYNC_LIBRARY

from nti.externalization.interfaces import LocatedExternalDict

from ..synchronize import synchronize

SYNC_LOCK_NAME = '/var/libraries/Lock/sync'

@view_config(permission=ACT_SYNC_LIBRARY)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='POST',
			   context=IDataserverFolder,
			   name='RemoveSyncLock')
class _RemoveSyncLock(AbstractAuthenticatedView):

	@Lazy
	def redis(self):
		return component.getUtility(IRedisClient)

	def __call__(self):
		self.redis.delete(SYNC_LOCK_NAME)
		return hexc.HTTPNoContent()

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
		# Fail fast if we cannot acquire the lock.
		lock = self.redis.lock(SYNC_LOCK_NAME, self.lock_timeout)
		acquired = lock.acquire(blocking=False)
		if acquired:
			return lock
		raise_json_error(self.request,
						 hexc.HTTPLocked,
						 {'Message': 'Sync already in progress',
						  'Code':'Exception'},
						 None)

	def _txn_id(self):
		return "txn.%s" % get_thread_ident()

	def _do_call(self):
		values = self.readInput()
		site = values.get('site')
		allowRemoval = values.get('allowRemoval') or u''
		allowRemoval = allowRemoval.lower() in TRUE_VALUES
		# things to sync
		for name in ('ntiids', 'ntiid', 'packages', 'package'):
			ntiids = values.get(name)
			if ntiids:
				break
		ntiids = set(ntiids.split()) if isinstance(ntiids, string_types) else ntiids
		ntiids = list(ntiids) if ntiids else ()

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

		# JZ - 8.2015 - Disabling interaction also prevents stream changes
		# from being broadcast (specifically topic creations). We've seen such
		# changes end up causing conflict issues when managing sessions. These
		# retries cause syncs to take much longer to perform.
		now = time.time()
		result = LocatedExternalDict()
		result['Transaction'] = self._txn_id()
		endInteraction()
		try:
			params, results = synchronize(sleep=self._SLEEP,
										  site=site,
										  ntiids=ntiids or (),
										  allowRemoval=allowRemoval)
			result['Params'] = params
			result['Results'] = results
		except (StandardError, Exception) as e:
			logger.exception("Failed to Sync")

			transaction.doom()  # cancel changes

			exc_type, exc_value, exc_traceback = sys.exc_info()
			result['Code'] = e.__class__.__name__
			result['Message'] = str(e)
			result['Traceback'] = repr(traceback.format_exception(exc_type,
																  exc_value,
																  exc_traceback))
			raise_json_error(self.request,
							 hexc.HTTPUnprocessableEntity,
							 result,
							 exc_traceback)
		finally:
			restoreInteraction()
			result['SyncTime'] = time.time() - now
		return result

	def __call__(self):
		logger.info('Acquiring sync lock')
		# With 'with', we deadlock while attempting to re-acquire the lock.
		lock = self.lock
		try:
			logger.info('Starting sync %s', self._txn_id())
			return self._do_call()
		finally:
			lock.release()
