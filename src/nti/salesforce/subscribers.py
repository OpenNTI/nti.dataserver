# -*- coding: utf-8 -*-
"""
Salesforce event subscribers

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.lifecycleevent.interfaces import IObjectCreatedEvent

from nti.assessment import interfaces as as_interfaces

@component.adapter(as_interfaces.IQAssessedQuestion, IObjectCreatedEvent)
def question_assessed(question, event):
	pass
