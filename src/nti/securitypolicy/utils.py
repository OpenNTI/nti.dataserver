#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

logger = __import__('logging').getLogger(__name__)


def is_impersonating(request):
    # We know we are impersonating if we have a 'REMOTE_USER_DATA' value in
    # the environ
    environ = getattr(request, 'environ', {})
    identity = environ.get('repoze.who.identity', {})
    # If currently in an impersonation request, this info will only exist
    # in the environ
    userdata = identity.get('userdata', {}) or environ.get('REMOTE_USER_DATA', {})
    return bool('username' in userdata and userdata.get('username'))
