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
    userdata = identity.get('userdata', {})
    return bool('username' in userdata and userdata.get('username'))
