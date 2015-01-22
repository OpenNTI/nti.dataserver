#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.dataserver.users import User
from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.externalization.interfaces import LocatedExternalDict

from nti.utils.maps import CaseInsensitiveDict

@view_config(route_name='objects.generic.traversal',
			   renderer='rest',
			   permission=nauth.ACT_NTI_ADMIN,
			   request_method='GET',
			   context=IDataserverFolder,
			   name='GetUserBlacklist')
class GetUserBlacklistView(AbstractAuthenticatedView):

	def __call__(self):
		user_blacklist = component.getUtility(IUserBlacklistedStorage)

		result = LocatedExternalDict()
		result.__name__ = self.request.view_name
		result.__parent__ = self.request.context
		result['Items'] = vals = {}

		count = 0
		for key, val in list(user_blacklist):
			vals[key] = val
			count += 1
		result['Count'] = count
		return result

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 permission=nauth.ACT_NTI_ADMIN,
			 request_method='POST',
			 context=IDataserverFolder,
			 name='RemoveFromUserBlacklist')
class RemoveFromUserBlacklistView(AbstractAuthenticatedView,
							   	  ModeledContentUploadRequestUtilsMixin):

	"""
	Remove username from blacklist.
	"""
	def __call__(self):
		values = CaseInsensitiveDict(self.readInput())
		username = values.get( 'username' ) or values.get('user')
		if not username:
			raise hexc.HTTPUnprocessableEntity("must specify a username")

		user_blacklist = component.getUtility(IUserBlacklistedStorage)
		did_remove = user_blacklist.remove_blacklist_for_user( username )

		result = LocatedExternalDict()
		result.__name__ = self.request.view_name
		result.__parent__ = self.request.context
		result['username'] = username
		result['did_remove'] = did_remove
		return result
	
@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 permission=nauth.ACT_NTI_ADMIN,
			 request_method='POST',
			 context=IDataserverFolder,
			 name='RemoveUser')
class RemoveUserView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	"""
	Remove a user
	"""

	def __call__(self):
		values = self.readInput()
		username = values.get('username') or values.get('user')
		if not username:
			raise hexc.HTTPUnprocessableEntity("must specify a username")
		
		user = User.get_user(username)
		if user is None or not IUser.providedBy(user):
			raise hexc.HTTPUnprocessableEntity("user not found")
		
		User.delete_user(username)
		return hexc.HTTPNoContent()
