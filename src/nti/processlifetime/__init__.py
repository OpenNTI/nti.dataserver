#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Events in the life time of a server process (an extension of :mod:`zope.processlifetime`).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

# Export these things
from zope.processlifetime import DatabaseOpened
from zope.processlifetime import IDatabaseOpened
from zope.processlifetime import ProcessStarting
from zope.processlifetime import IProcessStarting
from zope.processlifetime import DatabaseOpenedWithRoot
from zope.processlifetime import IDatabaseOpenedWithRoot 

# Assign to them to keep pylint from complaining

DatabaseOpened = DatabaseOpened
IDatabaseOpened = IDatabaseOpened

DatabaseOpenedWithRoot = DatabaseOpenedWithRoot
IDatabaseOpenedWithRoot = IDatabaseOpenedWithRoot

class IAfterDatabaseOpenedEvent(interface.Interface):
	"""
	In the startup sequence, this should be notified after the
	:class:`IDatabaseOpened` event has been notified for each
	database, but before the root is available. This allows the
	application a chance to do some intermediate processing.
	"""
	database = interface.Attribute("The main database.")

@interface.implementer(IAfterDatabaseOpenedEvent)
class AfterDatabaseOpenedEvent(object):

	def __init__(self, database):
		self.database = database

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

class IApplicationTransactionOpenedEvent(interface.Interface):
	"""
	An event fired during application startup, after :class:`IDatabaseOpenedWithRoot`
	has been fired (and so :mod:`zope.generations` installs and evolutions
	have been done), within the scope of a transaction manager, and within
	the scope of the application's main :class:`zope.component.interfaces.ISite`.

	This event is intended to allow additional (database) setup that cannot
	be handled with simple generations, or that need to take place every time
	the application starts. If the process is going to fork, this will be fired
	before the fork, in the main process.

	The transaction will be committed after this event has fired.

	.. note:: Unlike the database events, which repeat during process
		lifetime (such as after a fork, where the database must be re-opened)
		this event is only fired once during a particular application lifetime.
	"""

@interface.implementer(IApplicationTransactionOpenedEvent)
class ApplicationTransactionOpenedEvent(object):
	pass

class IApplicationProcessStarting(IProcessStarting):
	xml_conf_machine = interface.Attribute("The main database.")

@interface.implementer(IApplicationProcessStarting)
class ApplicationProcessStarting(ProcessStarting):
	
	def __init__(self, xml_conf_machine=None):
		self.xml_conf_machine = xml_conf_machine
