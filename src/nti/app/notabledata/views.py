#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from .adapters import IUserNotableData
from nti.appserver.interfaces import INamedLinkView
from nti.app.renderers.interfaces import IUGDExternalCollection
from nti.externalization.interfaces import LocatedExternalDict

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest

from nti.appserver.ugd_query_views import _UGDView

from nti.dataserver.authorization import ACT_READ
from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

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

	Notable objects include:

	* Direct replies to :class:`.IThreadable` objects I created;

	* Top-level objects directly shared to me;

	* Top-level objects created by certain people (people that are returned
		from subscription adapters to :class:`.IUserPresentationPriorityCreators`)


	An addition to the usual ``batchStart`` and ``batchSize`` parameters, you may also
	use:

	batchBefore
		If given, this is the timestamp (floating point number in fractional
		unix seconds, as returned in ``Last Modified``) of the *youngest*
		object to consider returning. Thus, the most efficient way to page through
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
	_DEFAULT_BATCH_SIZE = 100
	_DEFAULT_BATCH_START = 0

	def __call__( self ):
		request = self.request
		self.check_cross_user()
		# pre-flight the batch
		batch_size, batch_start = self._get_batch_size_start()
		limit = batch_start + batch_size + 2
		batch_before = None
		if self.request.params.get('batchBefore'):
			try:
				batch_before = float(self.request.params.get( 'batchBefore' ))
			except ValueError: # pragma no cover
				raise HTTPBadRequest()

		result = LocatedExternalDict()
		result['Last Modified'] = result.lastModified = 0
		result.__parent__ = self.request.context
		result.__name__ = self.ntiid
		result.mimeType = nti_mimetype_with_class( None )
		interface.alsoProvides( result, IUGDExternalCollection )

		user_notable_data = component.getMultiAdapter( (self.remoteUser, self.request),
													   IUserNotableData )
		safely_viewable_intids = user_notable_data.get_notable_intids()

		result['TotalItemCount'] = len(safely_viewable_intids)

		# Our best LastModified time will be that of the most recently
		# modified object; unfortunately, we have no way of tracking deletes...
		most_recently_modified_object = list(user_notable_data.iter_notable_intids(
			user_notable_data.sort_notable_intids(safely_viewable_intids,
												  field_name='lastModified',
												  limit=2,
												  reverse=True) ))
		if most_recently_modified_object:
			result['Last Modified'] = result.lastModified = most_recently_modified_object[0].lastModified

		# Also if we didn't have to provide TotalItemCount, our
		# handling of before could be much more efficient
		# (we could do this join early on)
		if batch_before is not None:
			safely_viewable_intids = user_notable_data.get_notable_intids(max_created_time=batch_before)

		sorted_intids = user_notable_data.sort_notable_intids( safely_viewable_intids,
															   limit=limit,
															   reverse=request.params.get('sortOrder') != 'ascending')

		items = user_notable_data.iter_notable_intids(sorted_intids)
		self._batch_tuple_iterable(result, items,
								   number_items_needed=limit,
								   batch_size=batch_size,
								   batch_start=batch_start,
								   selector=lambda x: x)
		_NotableUGDLastViewed.write_last_viewed(request, self.remoteUser, result)
		return result

from zope.annotation.interfaces import IAnnotations
from nti.dataserver.links import Link
from numbers import Number
from nti.externalization import interfaces as ext_interfaces


@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 request_method='PUT',
			 context='nti.appserver.interfaces.IRootPageContainerResource',
			 permission=ACT_READ,
			 name='lastViewed')
class _NotableUGDLastViewed(AbstractAuthenticatedView,
							ModeledContentUploadRequestUtilsMixin):
	"""
	Maintains the 'lastViewed' time for each user's NotableUGD.
	"""

	# JAM: I know we'll need to access this elsewhere, from
	# the emailing process, so there will need to be a more formal
	# API for this. Currently we're storing it as an annotation
	# on the user as a timestamp
	KEY = 'nti.appserver.ugd_query_views._NotableUGDLastViewed'

	inputClass = Number

	@classmethod
	def write_last_viewed(cls, request, remote_user, result):
		annotations = IAnnotations(remote_user)
		last_viewed = annotations.get(cls.KEY, 0)

		result['lastViewed'] = last_viewed
		links = result.setdefault(ext_interfaces.StandardExternalFields.LINKS, [])
		# If we use request.context to base the link on, which is really the Right Thing,
		# we break because when that externalizes, we get the canonical location
		# beneath NTIIDs instead of beneath Pages(NTIID)...which doesn't have
		# these views registered.
		path = request.path
		if not path.endswith('/'):
			path = path + '/'
		links.append( Link( path,
							rel='lastViewed',
							elements=('lastViewed',),
							method='PUT'))
		return result

	def _do_call(self):
		# Note that we don't use the user in the traversal path,
		# we use the user that's actually making the call.
		# This is why we can get away with just the READ permission.
		annotations = IAnnotations(self.remoteUser)
		last_viewed = annotations.get(self.KEY, 0)

		incoming_last_viewed = self.readInput()
		if incoming_last_viewed > last_viewed:
			last_viewed = incoming_last_viewed
			annotations[self.KEY] = incoming_last_viewed
		return incoming_last_viewed
