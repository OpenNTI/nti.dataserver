#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import isodate
from datetime import datetime

from zope import component

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.common.time import bit64_int_to_time
from nti.common.maps import CaseInsensitiveDict

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserverFolder
from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.dataserver import authorization as nauth

from nti.dataserver.users import User
from nti.dataserver.users.users_utils import remove_broken_objects

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from . import is_true

ITEMS = StandardExternalFields.ITEMS

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
		result[ITEMS] = vals = {}

		count = 0
		for key, val in list(user_blacklist):
			val = datetime.fromtimestamp(bit64_int_to_time(val))
			vals[key] = isodate.datetime_isoformat(val)
			count += 1
		result['Total'] = result['Count'] = count
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
			 name='RemoveUserBrokenObjects')
class RemoveUserBrokenObjects(AbstractAuthenticatedView, 
							  ModeledContentUploadRequestUtilsMixin):

	"""
	Remove user broken objects
	"""

	def __call__(self):
		values = CaseInsensitiveDict(self.readInput())
		username = values.get('username') or values.get('user')
		if not username:
			raise hexc.HTTPUnprocessableEntity("must specify a username")
		
		user = User.get_user(username)
		if user is None or not IUser.providedBy(user):
			raise hexc.HTTPUnprocessableEntity("user not found")
		
		containers = values.get('containers') or values.get('include_containers')
		containers = bool(not containers or is_true(containers))
		
		stream = values.get('stream') or values.get('include_stream')
		stream = is_true(stream)
		
		shared = values.get('shared') or values.get('include_shared')
		shared = is_true(shared)
		
		dynamic =  values.get('dynamic') or \
				   values.get('dynamic_friends') or \
				   values.get('include_dynamic') or \
				   values.get('include_dynamic_friends')
		dynamic = is_true(dynamic)
		
		data = remove_broken_objects(user, include_containers=containers,
									 include_stream=stream,
									 include_shared=shared,
									 include_dynamic_friends=dynamic)
		
		result = LocatedExternalDict()
		result[ITEMS] = data
		result['Total'] = result['Count'] = len(data)
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
		values = CaseInsensitiveDict(self.readInput())
		username = values.get('username') or values.get('user')
		if not username:
			raise hexc.HTTPUnprocessableEntity("must specify a username")
		
		user = User.get_user(username)
		if user is None or not IUser.providedBy(user):
			raise hexc.HTTPUnprocessableEntity("user not found")
		
		User.delete_user(username)
		return hexc.HTTPNoContent()
