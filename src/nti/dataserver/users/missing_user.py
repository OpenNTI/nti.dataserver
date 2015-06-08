#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and utilities for working with users that have gone
missing, presumably due to deletion.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from nti.common import create_gravatar_url

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IMissingUser
from nti.dataserver.interfaces import IMissingEntity
from nti.dataserver.users.interfaces import IUserProfile

from nti.zodb import minmax

@interface.implementer(IMissingEntity,
					   IUserProfile,
					   IAttributeAnnotatable)
class _TransientMissingEntity(object):
	"""
	A stand-in that represents a missing (probably deleted, but possibly never created)
	entity. This is not a	persistent object and is created at runtime as needed.
	"""

	__external_class_name__ = 'MissingEntity'

	alias = _('Missing Entity')
	realname = _('Deleted Entity')
	username = 'Missing Entity'  # spaces are illegal in real usernames so this can never resolve
	avatarURL = create_gravatar_url('Missing Entity@alias.nextthought.com')

	__name__ = username
	__parent__ = None

@interface.implementer(IUser, IMissingUser)
class _TransientMissingUser(_TransientMissingEntity):
	"""
	A stand-in that represents a missing (probably deleted, but possibly never created)
	user. This is not a	persistent object and is created at runtime as needed.
	"""

	__external_class_name__ = 'MissingUser'

	alias = _('Missing User')
	realname = _('Deleted User')
	username = 'Missing User'  # spaces are illegal in real usernames so this can never resolve
	avatarURL = create_gravatar_url('Missing User@alias.nextthought.com')

	lastLoginTime = minmax.ConstantZeroValue()
	notificationCount = minmax.ConstantZeroValue()

	following = ()
	communities = ()
	ignoring_shared_data_from = ()
	accepting_shared_data_from = ()

def MissingEntity(username):
	"""
	Return a missing entity proxy for the given username.
	"""
	return _TransientMissingEntity()  # Not cacheable due to annotations

def MissingUser(username):
	"""
	Return a missing user proxy for the given username.
	"""
	return _TransientMissingUser()  # Not cacheable due to annotations
