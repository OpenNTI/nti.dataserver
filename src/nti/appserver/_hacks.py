#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from .dataserver_pyramid_views import _UGDPutView as UGDPutView

from pyramid.view import view_config


from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver import authorization as nauth


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IFriendsList,
			  name='++fields++friends',
			  permission=nauth.ACT_UPDATE, request_method='PUT' )
class _FriendsListsFriendsFieldUpdateView(UGDPutView):
	"""
	This is a temporary fast hack to enable updating friends list objects
	with just friends using the new ++fields++ syntax until the unification
	is complete.

	This is done by specifically naming a view for the remainder of the path
	after a friends list.
	"""

	inputClass = list

	def _get_object_to_update( self ):
		return self.request.context

	def _transformInput( self, externalValue ):
		return {"friends": externalValue}
