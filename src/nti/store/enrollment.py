#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enrollment functionality

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.event import notify

from . import course
from . import purchase_order
from . import purchase_attempt
from . import purchase_history
from . import interfaces as store_interfaces

class CourseNotFoundException(Exception):
	pass

class UserNotEnrolledException(Exception):
	pass

class InvalidEnrollmentAttemptException(Exception):
	pass

def enroll_course(user, course_id, description=None, request=None):
	if course.get_course(course_id) is None:
		raise CourseNotFoundException()

	item = purchase_order.create_purchase_item(course_id, 1)
	order = purchase_order.create_purchase_order(item, quantity=1)
	purchase = purchase_attempt.create_errollment_attempt(order, description=description)
	
	if not purchase_history.has_history_by_item(user, course_id):
		purchase_history.register_purchase_attempt(purchase, user)
		notify(store_interfaces.EnrollmentAttemptSuccessful(purchase, request))
		return True
	return False

def unenroll_course(user, course_id, request=None):
	if course.get_course(course_id) is None:
		raise CourseNotFoundException()

	history = purchase_history.get_purchase_history_by_item(user, course_id)
	if not history or len(history) != 1:
		raise UserNotEnrolledException()
	else:
		purchase = history[0]
		if not store_interfaces.IEnrollmentPurchaseAttempt.providedBy(purchase):
			raise InvalidEnrollmentAttemptException()
		notify(store_interfaces.UnenrollmentAttemptSuccessful(purchase, request=request))
		purchase_history.remove_purchase_attempt(purchase, user)
		return True
	return False
