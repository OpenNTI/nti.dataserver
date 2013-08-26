#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Python RQ utils.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component
from zope import interface

from rq import Queue

from . import interfaces as nti_interfaces

@interface.implementer(nti_interfaces.IRQClient)
class _RQClient(object):

	def all_queues(self):
		connection = component.getUtility(nti_interfaces.IRedisClient)
		result = Queue.all(connection=connection)
		return result

	def create_queue(self, **kwargs):
		kwargs.pop('connection', None)
		connection = component.getUtility(nti_interfaces.IRedisClient)
		result = Queue(connection=connection, **kwargs)
		return result
