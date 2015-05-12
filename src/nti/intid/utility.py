#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains a :mod:`zc.intid.utility` derived utility for
managing intids. The primary reason to do this
is to provide better exceptions, and future proofing
of behaviour.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import BTrees

from zope import interface
from zope import event as zope_event

from zope.container.interfaces import IContained

from zope.security.proxy import removeSecurityProxy

from zc.intid.utility import AddedEvent
from zc.intid.utility import RemovedEvent
from zc.intid.utility import IntIds as _ZCIntIds

from nti.utils._compat import aq_base

from .interfaces import IntIdMissingError
from .interfaces import ObjectMissingError
from .interfaces import IntIdAlreadyInUseError

unwrap = removeSecurityProxy

# Make pylint not complain about "badly implemented container"
# pylint: disable=R0924

@interface.implementer(IContained)
class IntIds(_ZCIntIds):

	__name__ = None
	__parent__ = None

	family = BTrees.family64

	# Because this object stores IDs using attributes on the object,
	# it is important to be sure that the ID is not acquired
	# from a parent. Hence, all the methods use aq_base to unwrap
	# the object.
	# Removing all proxies in general is more tricky; sometimes a 
	# zope.container.contained.ContainedProxy is really what we want to register.
	# Fortunately, most proxies pass attributes on through to the underlying
	# object, in which case queryId will take either the proxy or the wrapped object;
	# alternatively, they define __slots__ and forbid new attributes

	def queryId(self, ob, default=None):
		"""
		NOTE: if you pass a broken object (in the ZODB sense),
		this will hide that fact. We have to activate it,
		but if it is broken, we will not be able to. However,
		we catch KeyError, which is a superclass of the POSKeyError
		that gets thrown, so you cannot distinguish it at this point.

		We do not change this for backwards compatibility.
		"""
		return _ZCIntIds.queryId(self, aq_base(ob), default=default)

	def register(self, ob, event=True):
		ob = aq_base(ob)
		ob = unwrap(ob)
		uid = self.queryId(ob)
		if uid is None:
			uid = self.generateId(ob)
			if uid in self.refs:
				raise ValueError("id generator returned used id")
		self.refs[uid] = ob
		setattr(ob, self.attribute, uid)
		if event:
			zope_event.notify(AddedEvent(ob, self, uid))
		return uid

	def unregister(self, ob, event=True):
		ob = unwrap(ob)
		uid = self.queryId(ob)
		if uid is None:
			return
		del self.refs[uid]
		setattr(ob, self.attribute, None)
		if event:
			zope_event.notify(RemovedEvent(ob, self, uid))

	def getId(self, ob):
		ob = aq_base(ob)
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
		unwrapped = unwrap(aq_base(ob))
		if uid in self.refs:
			raise IntIdAlreadyInUseError(ob)
		self.refs[uid] = unwrapped
		return uid

	def forceUnregister(self, uid, ob=None, notify=False, removeAttribute=True):
		if not uid in self.refs:
			raise KeyError(uid)
		
		if ob is not None:
			unwrapped = unwrap(aq_base(ob))
			if self.refs[uid] is not unwrapped:
				raise KeyError(ob)
	
		del self.refs[uid]
		
		if 	ob is not None and removeAttribute and \
			getattr(ob, self.attribute, None) is not None:
			setattr(ob, self.attribute, None)

		if notify and ob is not None:
			zope_event.notify(RemovedEvent(ob, self, uid))

	def __repr__( self ):
		return "<%s.%s (%s) %s/%s>" % (self.__class__.__module__,
									   self.__class__.__name__,
									   self.attribute,
									   self.__parent__, self.__name__)
