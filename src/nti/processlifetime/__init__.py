#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Events in the life time of a server process (an extension of :mod:`zope.processlifetime`).

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# Export these things
from zope.processlifetime import DatabaseOpened
from zope.processlifetime import IDatabaseOpened
from zope.processlifetime import ProcessStarting
from zope.processlifetime import IProcessStarting
from zope.processlifetime import DatabaseOpenedWithRoot
from zope.processlifetime import IDatabaseOpenedWithRoot

from nti.processlifetime.interfaces import AfterDatabaseOpenedEvent
from nti.processlifetime.interfaces import IAfterDatabaseOpenedEvent

from nti.processlifetime.interfaces import ProcessWillFork
from nti.processlifetime.interfaces import IProcessWillFork

from nti.processlifetime.interfaces import ProcessDidFork
from nti.processlifetime.interfaces import IProcessDidFork

from nti.processlifetime.interfaces import ApplicationTransactionOpenedEvent
from nti.processlifetime.interfaces import IApplicationTransactionOpenedEvent

from nti.processlifetime.interfaces import ApplicationProcessStarting
from nti.processlifetime.interfaces import IApplicationProcessStarting
