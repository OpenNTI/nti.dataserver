#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and utilities for working with users that have gone
missing, presumably due to deletion.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import interface

from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver import interfaces as nti_interfaces
from zope.annotation import interfaces as an_interfaces

from nti.zodb import minmax
from nti.utils import create_gravatar_url

@interface.implementer(nti_interfaces.IMissingEntity,
					   user_interfaces.IUserProfile,
					   an_interfaces.IAttributeAnnotatable)
class _TransientMissingEntity(object):
	"""
	A stand-in that represents a missing (probably deleted, but possibly never created)
	entity. This is not a	persistent object and is created at runtime as needed.
	"""

	__external_class_name__ = 'MissingEntity'

	alias = _('Missing Entity')
	realname = _('Deleted Entity')
	username = 'Missing Entity' # spaces are illegal in real usernames so this can never resolve
	__name__ = username
	__parent__ = None
	avatarURL = create_gravatar_url( 'Missing Entity@alias.nextthought.com' )


@interface.implementer(nti_interfaces.IUser,
					   nti_interfaces.IMissingUser )
class _TransientMissingUser(_TransientMissingEntity):
	"""
	A stand-in that represents a missing (probably deleted, but possibly never created)
	user. This is not a	persistent object and is created at runtime as needed.
	"""

	__external_class_name__ = 'MissingUser'

	alias = _('Missing User')
	realname = _('Deleted User')
	username = 'Missing User' # spaces are illegal in real usernames so this can never resolve
	avatarURL = create_gravatar_url( 'Missing User@alias.nextthought.com' )

	lastLoginTime = minmax.ConstantZeroValue()
	notificationCount = minmax.ConstantZeroValue()
	communities = ()
	following = ()
	ignoring_shared_data_from = ()
	accepting_shared_data_from = ()


def MissingEntity( username ):
	"""
	Return a missing entity proxy for the given username.
	"""
	return _TransientMissingEntity()  # Not cacheable due to annotations


def MissingUser( username ):
	"""
	Return a missing user proxy for the given username.
	"""
	return _TransientMissingUser() # Not cacheable due to annotations
