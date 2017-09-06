#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from zope import component

# re-exports
from nti.dataserver.activitystream_change import Change

from nti.dataserver.users.communities import Everyone
from nti.dataserver.users.communities import Community

from nti.dataserver.users.entity import Entity

from nti.dataserver.users.friends_lists import FriendsList
from nti.dataserver.users.friends_lists import DynamicFriendsList
from nti.dataserver.users.friends_lists import _FriendsListUsernameIterable

from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users.password import Password as _Password

from nti.dataserver.users.users import _DevicesMap
from nti.dataserver.users.users import _TranscriptsMap
from nti.dataserver.users.users import _FriendsListMap

from nti.dataserver.users.users import Device
from nti.dataserver.users.users import Principal

from nti.dataserver.users.users import User
from nti.dataserver.users.users import OpenIdUser
from nti.dataserver.users.users import FacebookUser

from nti.dataserver.users.users import onChange
from nti.dataserver.users.users import user_devicefeedback
from nti.dataserver.users.users import get_shared_dataserver as _get_shared_dataserver
