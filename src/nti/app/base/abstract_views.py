#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Abstract classes to be used as pyramid view callables.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.utils.property import Lazy

from nti.dataserver.interfaces import IDataserver

from nti.app.authentication import get_remote_user as _get_remote_user

class AbstractView(object):
	"""
	Base class for views. Defines the ``request``, ``context`` and ``dataserver``
	properties. To be a valid view callable, you must implement ``__call__``.
	"""

	def __init__(self, request):
		self.request = request

	@Lazy
	def context(self):
		return self.request.context

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
		return _get_remote_user( self.request, self.dataserver )

	@Lazy
	def remoteUser(self):
		"""
		Returns the remote user for the current request; cached on first use.
		"""
		return self.getRemoteUser()
