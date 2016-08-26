#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for writing process delegates that adhere to the
best practices defined in this package.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.mailer.interfaces import IVERP

from nti.property.property import Lazy

class AbstractBulkEmailProcessDelegate(object):
	"""
	Partial implementation of a process delegate.
	"""
	text_template_extension = ".txt"

	fromaddr = 'no-reply@alerts.nextthought.com'
	subject = '<No Subject>'

	def __init__(self, context, request):
		self.context = context
		self.request = request

	@Lazy
	def _verp(self):
		return component.getUtility(IVERP)

	def compute_fromaddr_for_recipient( self, recipient ):
		return self._verp.realname_from_recipients(
			self.fromaddr,
			(recipient['email'],),
			request=self.request)

	def compute_sender_for_recipient( self, recipient ):
		return self._verp.verp_from_recipients(
			self.fromaddr,
			(recipient['email'],),
			request=self.request)

	def compute_template_args_for_recipient(self, recipient ):
		# By default, we return *something* non-None so that we
		# still get sent
		return recipient.get('template_args', {})

	def compute_subject_for_recipient(self, recpient):
		return self.subject
