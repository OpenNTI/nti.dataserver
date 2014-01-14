#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enrollment functionality

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
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

def get_enrollment(user, course_id):
	history = purchase_history.get_purchase_history_by_item(user, course_id)
	for enrollment in history or ():
		if store_interfaces.IEnrollmentPurchaseAttempt.providedBy(enrollment):
			return enrollment
	return None

def is_enrolled(user, course_id):
	enrollment = get_enrollment(user, course_id)
	return enrollment is not None

def do_enrollment(user, course_id, description=None, request=None, registry=component):
	item = purchase_order.create_purchase_item(course_id, 1)
	order = purchase_order.create_purchase_order(item, quantity=1)
	purchase = purchase_attempt.create_enrollment_attempt(order, description=description)
	if not is_enrolled(user, course_id):
		purchase_history.register_purchase_attempt(purchase, user)
		notify(store_interfaces.EnrollmentAttemptSuccessful(purchase, request))
		return True
	return False

def enroll_course(user, course_id, description=None, request=None, registry=component):
	if course.get_course(course_id, registry) is None:
		raise CourseNotFoundException()
	return do_enrollment(user, course_id, description, request, registry)

def unenroll_course(user, course_id, request=None, registry=component):
	if course.get_course(course_id, registry) is None:
		raise CourseNotFoundException()

	enrollment = get_enrollment(user, course_id)
	if enrollment is None:
		logger.debug("user %s is not enrolled in course %s" % (user, course_id))
		raise UserNotEnrolledException()

	purchase = enrollment
	assert store_interfaces.IEnrollmentPurchaseAttempt.providedBy(purchase)

	purchase_history.remove_purchase_attempt(purchase, user)
	notify(store_interfaces.UnenrollmentAttemptSuccessful(purchase, request=request))
	return True
