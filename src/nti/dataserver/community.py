#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.app.users.zope_security",
    "nti.app.users.zope_security",
    "PersistentCommunityPrincipalRoleManager",
    "PersistentCommunityRolePermissionManager",
)
