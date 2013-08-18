#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains a :mod:`zc.intid.utility` derived utility for
managing intids. The primary reason to do this
is to provide better exceptions, and future proofing
of behaviour.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import event as zope_event
from zope.container.interfaces import IContained
from zope.security.proxy import removeSecurityProxy

from zc.intid.utility import IntIds as _ZCIntIds

from nti.utils._compat import aq_base

from .interfaces import IntIdMissingError
from .interfaces import ObjectMissingError
from .interfaces import IntIdAlreadyInUseError

unwrap = removeSecurityProxy

# Make pylint not complain about "badly implemented container"
#pylint: disable=R0924

@interface.implementer(IContained)
class IntIds(_ZCIntIds):

	__name__ = None
	__parent__ = None

	# Because this object stores IDs using attributes on the object,
	# it is important to be sure that the ID is not acquired
	# from a parent. Hence, all the methods use aq_base to unwrap
	# the object.
	# Removing all proxies in general is more tricky; sometimes a zope.container.contained.ContainedProxy
	# is really what we want to register. Fortunately, most
	# proxies pass attributes on through to the underlying
	# object, in which case queryId will take either the proxy or the wrapped object;
	# alternatively, they define __slots__ and forbid new attributes

	def queryId(self, ob, default=None):
		return _ZCIntIds.queryId(self, aq_base(ob), default=default)

	def register(self, ob):
		return _ZCIntIds.register(self, aq_base(ob))

	def getId(self, ob):
		ob = aq_base( ob )
		try:
			return _ZCIntIds.getId(self, ob)
		except KeyError:
			raise IntIdMissingError(ob, id(ob), self)

	def getObject(self, ID):
		try:
			return _ZCIntIds.getObject(self, ID)
		except KeyError:
			raise ObjectMissingError(ID, self)

	def forceRegister(self, uid, ob):
		unwrapped = unwrap(ob)
		if uid in self.refs:
			raise IntIdAlreadyInUseError(ob)
		self.refs[uid] = unwrapped
		return uid

	def forceUnregister(self, uid, ob, notify=False):
		unwrapped = unwrap(ob)
		if not uid in self.refs or self.refs[uid] is not unwrapped:
			raise KeyError(ob)
		del self.refs[uid]
		setattr(ob, self.attribute, None)
		if notify:
			zope_event.notify(_ZCIntIds.RemovedEvent(ob, self, uid))

	def __repr__( self ):
		return "<%s.%s (%s) %s/%s>" % (self.__class__.__module__, self.__class__.__name__,
									   self.attribute,
									   self.__parent__, self.__name__)
