#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User export views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import simplejson

from pyramid.view import view_config

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.externalization.datastructures import LocatedExternalDict

@view_config(route_name='objects.generic.traversal',
			 name='get_preferences',
			 request_method='GET',
			 renderer='rest',
			 context=nti_interfaces.IUser,
			 permission=nauth.ACT_READ)
def get_preferences(request):
	username = request.context.username
	user = users.User.get_user(username)
	preferences = user_interfaces.IEntityPreferences(user, None) or {}
	result = LocatedExternalDict()
	result['Items'] = dict(preferences)
	return result

@view_config(route_name='objects.generic.traversal',
			 name='set_preferences',
			 request_method='POST',
			 renderer='rest',
			 context=nti_interfaces.IUser,
			 permission=nauth.ACT_UPDATE)
def set_preferences(request):
	values = simplejson.loads(unicode(request.body, request.charset))
	username = request.context.username
	user = users.User.get_user(username)
	preferences = user_interfaces.IEntityPreferences(user)
	preferences.update(values)
	result = LocatedExternalDict()
	result['Items'] = dict(preferences)
	return result

@view_config(route_name='objects.generic.traversal',
			 name='delete_preferences',
			 request_method='DELETE',
			 renderer='rest',
			 context=nti_interfaces.IUser,
			 permission=nauth.ACT_DELETE)
def delete_preferences(request):
	values = simplejson.loads(unicode(request.body, request.charset)) if request.body else ()
	username = request.context.username
	user = users.User.get_user(username)
	preferences = user_interfaces.IEntityPreferences(user)
	if not values:
		keys = list(preferences.keys())
	else:
		keys = values.get('keys', list(values.keys()))
		keys = list(preferences.keys()) if not keys or keys == "*" else keys

	if isinstance(keys, six.string_types):
		keys = keys.split()

	for key in keys:
		if key in preferences:
			del preferences[key]

	result = LocatedExternalDict()
	result['Items'] = dict(preferences)
	return result

