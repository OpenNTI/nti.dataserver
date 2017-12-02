#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZCML directives relating to capabilities.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope.component.zcml import utility

from zope.security.zcml import IPermissionDirective

from nti.appserver.capabilities.capability import Capability

from nti.appserver.capabilities.interfaces import ICapability

from nti.base._compat import text_

logger = __import__('logging').getLogger(__name__)


class IRegisterCapabilityDirective(IPermissionDirective):
    """
    Register a capability.
    """


def registerCapability(_context, title, description=u'', **kwargs):
    cap_id = kwargs.get('id') or kwargs.get('name')
    assert cap_id, 'must provide a capability id'
    capability = Capability(text_(cap_id), 
                            text_(title), 
                            text_(description))
    utility(_context, provides=ICapability, component=capability, name=cap_id)
