#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to user activity.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from .ugd_query_views import _RecursiveUGDView as RecursiveUGDQueryView
from .httpexceptions import HTTPNotFound

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces
from nti.ntiids import ntiids

from nti.dataserver import authorization as nauth
from pyramid.view import view_config


#: The link relationship type for a link to retrieve activity
#: for a particular user.
#: Also serves as a view name for that same purpose
#: (:class:`UserActivityGetView`).
REL_USER_ACTIVITY = "Activity" # This permits a URL like .../users/$USER/Activity


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
	the UGD views. """


	def __init__( self, request ):
		self.request = request
		super(UserActivityGetView,self).__init__( request, the_user=request.context, the_ntiid=ntiids.ROOT )

	def _get_filter_names( self ):
		filters = set(super(UserActivityGetView,self)._get_filter_names())
		filters.add( 'MeOnly' )
		return filters


	def getObjectsForId( self, *args ):
		# Collect the UGD recursively
		try:
			result = list( super(UserActivityGetView,self).getObjectsForId(*args) )
		except HTTPNotFound:
			# There is always activity, it just may be empty
			result = []
		# Add the blog
		result.append( frm_interfaces.IPersonalBlog( self.user ) )
		return result
