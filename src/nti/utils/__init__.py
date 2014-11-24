#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from .gravatar import create_gravatar_url

from .gravatar import _AVATAR_SERVICES
from .gravatar import KNOWN_GRAVATAR_TYPES
from .gravatar import GENERATED_GRAVATAR_TYPES

from .chameleon import make_cache_dir
from .chameleon import setupChameleonCache

