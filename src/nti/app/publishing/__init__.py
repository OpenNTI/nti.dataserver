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

#: Publish view name
VIEW_PUBLISH = u"publish"

#: Unpublish view name
VIEW_UNPUBLISH = u"unpublish"

#: Publish transaction type
TRX_TYPE_PUBLISH = u'publish'

#: Unpublish transaction type
TRX_TYPE_UNPUBLISH = u'unpublish'
