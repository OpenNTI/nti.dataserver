#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
from numbers import Number

from zope import component
from zope import interface

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPNoContent

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.notabledata.adapters import IUserNotableData

from nti.app.renderers.interfaces import IUGDExternalCollection

from nti.appserver.interfaces import INamedLinkView

from nti.appserver.ugd_query_views import _UGDView

from nti.dataserver.authorization import ACT_READ

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.links.links import Link

from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.securitypolicy.utils import is_impersonating

LAST_MODIFIED = StandardExternalFields.LAST_MODIFIED
_NOTABLE_NAME = 'RUGDByOthersThatIMightBeInterestedIn'

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 request_method='GET',
			 context='nti.appserver.interfaces.IRootPageContainerResource',
			 permission=ACT_READ,
			 name=_NOTABLE_NAME)
@interface.implementer(INamedLinkView)
class _NotableRecursiveUGDView(_UGDView):
	"""
	A view of things that might be of interest to the remote user.
	This definition is fixed by the server, so client-applied filters
	are not supported. This view is intended to be used for \"notifications\"
	or as a special type of \"stream\", so sorting is also defined by the server
	as lastModified/descending (newest first) (although you can set ``sortOrder``
	to ``ascending``).

	In addition to the usual ``batchStart`` and ``batchSize`` parameters, you may also
	use:

	batchBefore
		If given, this is the timestamp (floating point number in fractional
		unix seconds, as returned in ``Last Modified``) of the *youngest*
		object to consider returning (exclusive). Thus, the most efficient way to page through
		this object is to *not* use ``batchStart``, but instead to set ``batchBefore``
		to the timestamp of the *oldest* change in the previous batch (always leaving
		``batchStart`` at zero). Effectively, this defaults to the current time.
		(Note: the next/previous link relations do not currently take this into account.)

	"""

	# We inherit from _UGDView to pick up some useful functions, but
	# we don't actually use much of it. In particular, we answer all
	# of our queries with the catalog.

	_support_cross_user = False
	_force_apply_security = True

	# Default to paging us
	_DEFAULT_BATCH_START = 0
	_DEFAULT_BATCH_SIZE = 100

	def __call__(self):
		request = self.request
		self.check_cross_user()
		# pre-flight the batch
		batch_size, batch_start = self._get_batch_size_start()
		limit = batch_start + batch_size + 2
		batch_before = None
		if self.request.params.get('batchBefore'):
			try:
				batch_before = float(self.request.params.get('batchBefore'))
			except ValueError:  # pragma no cover
				raise HTTPBadRequest()

		user_notable_data = component.getMultiAdapter((self.remoteUser, self.request),
													   IUserNotableData)

		result = LocatedExternalDict()
		result.__name__ = self.ntiid
		result.__parent__ = self.request.context
		result[LAST_MODIFIED] = result.lastModified = 0
		result.mimeType = nti_mimetype_with_class(None)
		interface.alsoProvides(result, IUGDExternalCollection)

		safely_viewable_intids = user_notable_data.get_notable_intids()

		result['TotalItemCount'] = len(safely_viewable_intids)

		# Our best LastModified time will be that of the most recently
		# modified object; unfortunately, we have no way of tracking deletes...
		most_recently_modified_object = list(user_notable_data.iter_notable_intids(
			user_notable_data.sort_notable_intids(safely_viewable_intids,
												  field_name='lastModified',
												  limit=2,
												  reverse=True)))
		if most_recently_modified_object:
			result[LAST_MODIFIED] = result.lastModified = most_recently_modified_object[0].lastModified

		descending_sort = request.params.get('sortOrder') != 'ascending'
		sorted_intids = user_notable_data.sort_notable_intids(safely_viewable_intids,
															  limit=limit,
															  reverse=descending_sort)
		items = user_notable_data.iter_notable_intids(sorted_intids)

		# It is usually faster and simpler to handle batch_before ourselves,
		# especially since the users are only browsing the first few pages.
		if batch_before is not None:
			# Exclusive to make sure clients do not have dupes.
			items = (x for x in items if x.createdTime < batch_before)
		self._batch_items_iterable(result, items,
								   number_items_needed=limit,
								   batch_size=batch_size,
								   batch_start=batch_start)
		# Note that we insert lastViewed into the result set as a convenience,
		# but we don't change the last-modified header based on this;
		# eventually we want this to go away (?)
		_NotableUGDLastViewed.write_last_viewed(request, user_notable_data, result)
		return result

@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   context='nti.appserver.interfaces.IRootPageContainerResource',
			   permission=ACT_READ,
			   name='lastViewed')
class _NotableUGDLastViewed(AbstractAuthenticatedView,
							ModeledContentUploadRequestUtilsMixin):
	"""
	Maintains the 'lastViewed' time for each user's NotableUGD.
	"""

	inputClass = Number

	@classmethod
	def write_last_viewed(cls, request, user_notable_data, result):
		last_viewed = user_notable_data.lastViewed

		result['lastViewed'] = last_viewed
		links = result.setdefault(StandardExternalFields.LINKS, [])
		# If we use request.context to base the link on, which is really the Right Thing,
		# we break because when that externalizes, we get the canonical location
		# beneath NTIIDs instead of beneath Pages(NTIID)...which doesn't have
		# these views registered.
		path = request.path

		links.append(Link(path,
						  rel='lastViewed',
						  elements=('lastViewed',),
						  method='PUT'))
		return result

	@property
	def _notable_data(self):
		# Note that we don't use the user in the traversal path,
		# we use the user that's actually making the call.
		# This is why we can get away with just the READ permission.
		user_notable_data = component.getMultiAdapter((self.remoteUser, self.request),
													   IUserNotableData)
		return user_notable_data

	@view_config(request_method='PUT')
	def __call__(self):
		return super(_NotableUGDLastViewed, self).__call__()

	def _do_call(self):
		if is_impersonating(self.request):
			logger.warn('Not setting lastViewed for impersonating user (%s)', self.remoteUser)
			return HTTPNoContent()

		user_notable_data = self._notable_data

		incoming_last_viewed = self.readInput()
		if incoming_last_viewed > user_notable_data.lastViewed:
			# We normalize to our time, assuming they were going forward.
			# This will make sure that all time comparisons are consistent.
			user_notable_data.lastViewed = time.time()
		return user_notable_data.lastViewed

	@view_config(request_method='GET')
	def _do_get(self):
		last_viewed = self._notable_data.lastViewed
		self.request.response.last_modified = last_viewed
		return last_viewed
