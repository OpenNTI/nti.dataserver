#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from nti.appserver.policies.interfaces import ICommunitySitePolicyUserEventListener

from nti.externalization.datastructures import InterfaceObjectIO

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class PolicyUserEventListenerExternalizer(InterfaceObjectIO):

    _ext_iface_upper_bound = ICommunitySitePolicyUserEventListener
