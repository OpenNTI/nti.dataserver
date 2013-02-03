#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Events in the life time of a server process (an extension of :mod:`zope.processlifetime`).

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#logger = __import__('logging').getLogger(__name__)

from zope import interface

# Export these things
from zope.processlifetime import IDatabaseOpened, DatabaseOpened
from zope.processlifetime import IDatabaseOpenedWithRoot, DatabaseOpenedWithRoot
from zope.processlifetime import IProcessStarting, ProcessStarting

# Assign to them to keep pylint from complaining
IDatabaseOpenedWithRoot = IDatabaseOpenedWithRoot
DatabaseOpenedWithRoot = DatabaseOpenedWithRoot
IDatabaseOpened = IDatabaseOpened
DatabaseOpened = DatabaseOpened
IProcessStarting = IProcessStarting
ProcessStarting = ProcessStarting


class IProcessWillFork(interface.Interface):
	"""
	An event that *may* be fired (on best effort basis) in a parent process
	before a call to :func:`os.fork`
	"""

@interface.implementer(IProcessWillFork)
class ProcessWillFork(object):
	pass

class IProcessDidFork(interface.Interface):
	"""
	An event that *may* be fired (on best effort basis) in the *child* process
	following a call to :func:`os.fork`. The timing (how soon after the fork)
	of this event is not defined.
	"""


@interface.implementer(IProcessDidFork)
class ProcessDidFork(object):
	pass
