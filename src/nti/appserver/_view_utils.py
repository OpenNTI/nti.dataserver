#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities relating to views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import component
from zope.cachedescriptors.property import Lazy

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
		result = users.User.get_user(request.authenticated_userid, dataserver=dataserver)
	return result

class AbstractView(object):
	"""
	Base class for views. Defines the ``request`` and ``dataserver`` property.
	"""
	def __init__(self, request):
		self.request = request

	@Lazy
	def dataserver(self):
		return component.getUtility(IDataserver)


class AbstractAuthenticatedView(AbstractView):
	"""
	Base class for views that expect authentication to be required.
	"""

	def getRemoteUser( self ):
		"""
		Returns the user object corresponding to the currently authenticated
		request.
		"""
		return get_remote_user( self.request, self.dataserver )

	@Lazy
	def remoteUser(self):
		"""
		Returns the remote user for the current request; cached on first use.
		"""
		return self.getRemoteUser()

import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
	"Moved to nti.app.externalization.view_mixins",
	"nti.app.externalization.view_mixins",
	"UploadRequestUtilsMixin",
	"ModeledContentUploadRequestUtilsMixin",
	"ModeledContentEditRequestUtilsMixin")
