#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. Id: __init__.py 13812 2012-11-07 23:14:01Z jason.madden $
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')
