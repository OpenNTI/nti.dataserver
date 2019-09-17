#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from nti.dataserver.users.interfaces import ICommunityPolicyManagementUtility

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ICommunityPolicyManagementUtility)
class DefaultCommunityPolicyManagementUtility(object):

    max_community_limit = 12

