#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to user activity.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from zope.annotation import factory as an_factory

from .ugd_query_views import _RecursiveUGDView as RecursiveUGDQueryView
from .ugd_query_views import _toplevel_filter
from .httpexceptions import HTTPNotFound

from nti.appserver import interfaces as app_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.interfaces import IDeletedObjectPlaceholder
from nti.ntiids import ntiids

from nti.dataserver import authorization as nauth
from pyramid.view import view_config

from nti.intid.containers import IntidContainedStorage

#: The link relationship type for a link to retrieve activity
#: for a particular user.
#: Also serves as a view name for that same purpose
#: (:class:`UserActivityGetView`).
REL_USER_ACTIVITY = "Activity" # This permits a URL like .../users/$USER/Activity

def _always_toplevel_filter( x ):
	try:
		# IInspectableWeakThreadable required for this
		return not x.isOrWasChildInThread()
	except AttributeError:
		return _toplevel_filter( x )



@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  permission=nauth.ACT_READ,
			  context=nti_interfaces.IUser,
			  name=REL_USER_ACTIVITY,
			  request_method='GET' )
class UserActivityGetView(RecursiveUGDQueryView):
	"""
	The /Activity view for a particular user.

	This view returns a collection of activity for the specified user, across
	the entire site (similar to a RecursiveUserGeneratedData query using the Root
	ntiid.) One difference is that this URL never returns a 404 response, even when initially
	empty. Another is that the ``MeOnly`` filter is implicit, and refers not to the calling
	user but the user who's data is being accessed.

	The contents fully support the same sorting and paging parameters as
	the UGD views with a few exceptions:

	* The definition for a ``TopLevel`` object is changed to mean one that has never been a
	  child in a thread (instead of just one who is not currently a child in a thread) (where possible).

	"""

	result_iface = app_interfaces.IUserActivityExternalCollection

	FILTER_NAMES = RecursiveUGDQueryView.FILTER_NAMES.copy()
	FILTER_NAMES['TopLevel'] = _always_toplevel_filter
	FILTER_NAMES['_NotDeleted'] = lambda x: not IDeletedObjectPlaceholder.providedBy( x )

	def __init__( self, request ):
		self.request = request
		super(UserActivityGetView,self).__init__( request, the_user=request.context, the_ntiid=ntiids.ROOT )

	def _get_filter_names( self ):
		filters = set(super(UserActivityGetView,self)._get_filter_names())
		filters.add( 'MeOnly' )
		filters.add( '_NotDeleted' )
		return filters


	def getObjectsForId( self, user, ntiid ):
		# Collect the UGD recursively
		try:
			result = list( super(UserActivityGetView,self).getObjectsForId(user, ntiid) )
		except HTTPNotFound:
			# There is always activity, it just may be empty
			result = []
		# Add the blog (possibly missing)
		# NOTE: This is no longer necessary as the blog is being treated as a container
		# found in user.containers with an NTIID
		#result.append( frm_interfaces.IPersonalBlog( self.user, () ) )

		# However, we do need to add the activity, if it exists
		# FIXME: Note that right now, we are only querying the global store (all the recursion
		# and iteration is handled in the super). This is probably easy to fix,
		# but we are also only using the global store (see forum_views)
		activity_provider = component.queryMultiAdapter( (user, self.request), app_interfaces.IUserActivityProvider )
		if activity_provider:
			result.append( activity_provider.getActivity() )
		return result

# TODO: This is almost certainly the wrong place for this
@interface.implementer(app_interfaces.IUserActivityStorage)
@component.adapter(nti_interfaces.IUser)
class DefaultUserActivityStorage(IntidContainedStorage):
	pass

DefaultUserActivityStorageFactory = an_factory(DefaultUserActivityStorage)

@interface.implementer(app_interfaces.IUserActivityProvider)
class DefaultUserActivityProvider(object):

	def __init__( self, user, request ):
		self.user = user

	def getActivity( self ):
		activity = app_interfaces.IUserActivityStorage( self.user, None )
		if activity is not None:
			return activity.getContainer( '', () )
