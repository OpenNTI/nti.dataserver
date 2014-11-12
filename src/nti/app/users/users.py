#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rendering for a REST-based client.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.dataserver.users.interfaces import IWillCreateNewEntityEvent

from nti.schema.interfaces import InvalidValue

class BlacklistedUsername(InvalidValue): pass

@component.adapter( IUser, IWillCreateNewEntityEvent )
def new_user_is_not_blacklisted(user, event):
	"""
	Verify that this new user does not exist in our blacklist of former users.
	"""
	user_blacklist = component.getUtility( IUserBlacklistedStorage )

	if user_blacklist.is_user_blacklisted( user ):
		raise BlacklistedUsername( user.username )
