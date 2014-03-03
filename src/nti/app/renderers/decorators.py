#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Decorator helpers for :mod:`nti.externalization` that are
used when externalizing for a remote client.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from abc import ABCMeta
from abc import abstractmethod

from nti.utils.property import alias

class AbstractRequestAwareDecorator(object):
	"""
	A base class providing support for decorators that
	are request-aware. Subclasses can be registered
	as either :class:`.IExternalMappingDecorator` objects
	or :class:`.IExternalObjectDecorator` objects and this
	class will unify the interface.
	"""

	__metaclass__ = ABCMeta

	def __init__(self, context, request):
		self.request = request

	def _predicate(self, context, result):
		"You may implement this method to check a precondition, return False if no decoration."
		return True

	def decorateExternalMapping( self, context, result ):
		if self._predicate(context, result):
			self._do_decorate_external(context, result)

	decorateExternalObject = alias('decorateExternalMapping')

	@abstractmethod
	def _do_decorate_external(self, context, result):
		"Implement this to do your actual decoration"
		raise NotImplementedError()


from nti.utils.property import Lazy
# XXX FIXME: This needs to move, probably
# to nti.app.authentication
from nti.appserver._view_utils import get_remote_user

class AbstractAuthenticatedRequestAwareDecorator(AbstractRequestAwareDecorator):
	"""
	A base class that ensures authenticated requests.

	When you subclass, remember to call this class's
	:meth:`_predicate`. For convenience and speed (to avoid needing
	to use ``super``) that can also be spelled as
	:attr:`_is_authenticated`

	"""

	# Notice these two methods have the same implementation
	# but do not call each other, for speed.
	def _predicate(self, context, result):
		return bool(self.authenticated_userid)
	@Lazy
	def _is_authenticated(self):
		return bool(self.authenticated_userid)

	@Lazy
	def remoteUser(self):
		return get_remote_user(self.request)

	@property
	def authenticated_userid(self):
		return self.request.authenticated_userid
