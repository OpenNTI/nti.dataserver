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
from zope.intid.interfaces import IIntIds

from nti.app.authentication import get_remote_user as _get_remote_user

from nti.dataserver.interfaces import IDataserver

from nti.utils.property import Lazy

def make_sharing_security_check(request, remoteUser):
	"""
	Return a callable object of one argument that returns true if the
	argument is readable to the current remote user.

	Note that this is *NOT* a full ACL or security policy check, it is optimized
	for speed and should only be used with a set of objects for which we know
	the sharing model is appropriate. (We do fall back to the full security
	check if all our attempts to determine sharing fail.)

	As an implementation details, if the ``isSharedWith`` method, used in the general
	case, is known to be slow, a method called ``xxx_isReadableByAnyIdOfUser``
	that takes three arguments (remote user, the intids of the current user and
	his memberships, and the BTree family of these sets) can be defined instead.
	(The intids of the user and his memberships are defined in another
	private property ``xxx_intids_of_memberships_and_self`` defined elsewhere.)
	"""

	remote_request = request
	remote_user = remoteUser
	family = component.getUtility(IIntIds).family
	my_ids = remoteUser.xxx_intids_of_memberships_and_self

	# XXX Deferred import to avoid a cycle. This will move to an nti.app
	# package, and this entire method may move with it too.
	from nti.appserver.pyramid_authorization import is_readable

	def security_check(x):
		try:
			if remote_user == x.creator:
				return True
		except AttributeError:
			pass
		try:
			return x.xxx_isReadableByAnyIdOfUser(remote_user, my_ids, family)
		except (AttributeError, TypeError):
			try:
				return x.isSharedWith(remote_user) # TODO: Might need to OR this with is_readable?
			except AttributeError:
				return is_readable(x, remote_request)
	return security_check


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


class AuthenticatedViewMixin(object):
	"""
	Mixin class for views that expect to be authenticated.
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

	def make_sharing_security_check(self):
		result = make_sharing_security_check(self.request, self.remoteUser)
		return result

class AbstractAuthenticatedView(AbstractView, AuthenticatedViewMixin):
	"""
	Base class for views that expect authentication to be required.
	"""
