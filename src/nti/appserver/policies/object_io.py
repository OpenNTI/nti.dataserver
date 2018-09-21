#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.appserver.policies.interfaces import ICommunitySitePolicyUserEventListener

from nti.externalization.datastructures import InterfaceObjectIO

logger = __import__('logging').getLogger(__name__)


class SitePolicyUserEventListenerObjectIO(InterfaceObjectIO):
    _ext_iface_upper_bound = ICommunitySitePolicyUserEventListener
