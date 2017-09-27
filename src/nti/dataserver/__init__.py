#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

# Note that we're not exporting anything by importing it.
# This helps reduce the chances of import cycles

from zope.i18nmessageid import MessageFactory
MessageFactory = MessageFactory('nti.dataserver')

SESSION_CLEANUP_QUEUE = u'nti.sessions/maintenance'
