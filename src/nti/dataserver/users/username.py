#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six
import uuid

from zope import interface

from nti.dataserver.users.interfaces import IUsernameGeneratorUtility

from nti.dataserver.users.users import User

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IUsernameGeneratorUtility)
class OpaqueUsernameGeneratorUtility(object):
    """
    Generate a unique, opaque username.
    """

    def _make_username(self):
        return six.text_type(uuid.uuid4().get_time_low())

    def generate_username(self):
        username = self._make_username()
        while User.get_user(username) is not None:
            username = self._make_username()
        return username
