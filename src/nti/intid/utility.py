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

from zope import interface

from zope.event import notify

from zope.security.proxy import removeSecurityProxy as unwrap

from zc.intid.interfaces import AddedEvent
from zc.intid.interfaces import RemovedEvent
from zc.intid.interfaces import IntIdInUseError

from zc.intid.utility import IntIds as _ZCIntIds

try:
	from Acquisition import aq_base
except ImportError:
	def aq_base(o):
		return o

import BTrees

from nti.intid.interfaces import IIntIds

import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecated(
	"Import from zope.intid.interfaces instead",
	IntIdMissingError='zope.intid.interfaces:IntIdMissingError',
	ObjectMissingError='zope.intid.interfaces:ObjectMissingError')

# Make pylint not complain about "badly implemented container"
# pylint: disable=R0924

@interface.implementer(IIntIds)
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
		ob = unwrap(aq_base(ob))
		uid = self.queryId(ob)
		if uid is None:
			uid = self.generateId(ob)
			if uid in self.refs:
				raise IntIdInUseError("id generator returned used id")
		self.refs[uid] = ob
		try:
			setattr(ob, self.attribute, uid)
		except:
			# cleanup our mess
			del self.refs[uid]
			raise
		if event:
			notify(AddedEvent(ob, self, uid))
		return uid

	def unregister(self, ob, event=True):
		ob = unwrap(ob)
		uid = self.queryId(ob)
		if uid is None:
			return
		# This should not raise KeyError, we checked that in queryId
		del self.refs[uid]
		setattr(ob, self.attribute, None)
		if event:
			notify(RemovedEvent(ob, self, uid))

	def getId(self, ob):
		return _ZCIntIds.getId(self, aq_base(ob))

	def forceRegister(self, uid, ob, check=True):
		unwrapped = unwrap(aq_base(ob))
		if check and uid in self.refs:
			raise IntIdInUseError(ob)
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

		if 		removeAttribute \
			and ob is not None \
			and getattr(ob, self.attribute, None) is not None:
			setattr(ob, self.attribute, None)

		if notify and ob is not None:
			notify(RemovedEvent(ob, self, uid))

	def __repr__(self):
		return "<%s.%s (%s) %s/%s>" % (self.__class__.__module__,
									   self.__class__.__name__,
									   self.attribute,
									   self.__parent__, self.__name__)
