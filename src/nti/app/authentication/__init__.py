#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Application-level authentication.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from pyramid.threadlocal import get_current_request

from nti.dataserver import users
from nti.dataserver.interfaces import IDataserver

def get_remote_user(request=None, dataserver=None):
	"""
	Returns the user object corresponding to the authenticated user of the
	request, or None (if there is no request or no dataserver or no such user)
	"""
	request = request or get_current_request()
	dataserver = dataserver or component.queryUtility( IDataserver )

	result = None
	if request is not None and dataserver is not None:
		username = request.authenticated_userid or u''
		result = users.User.get_user(username, dataserver=dataserver)
	return result
