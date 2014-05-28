#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Processors for :mod:`repoze.sendmail`, intended as a drop-in replacement
for the ``qp`` command line, using Amazon SES.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

import smtplib
from email.message import Message
import boto.ses

from boto.ses.exceptions import SESAddressBlacklistedError

from nti.utils.property import Lazy

from repoze.sendmail.interfaces import IMailer
from repoze.sendmail.encoding import encode_message
from repoze.sendmail.queue import ConsoleApp as _ConsoleApp

@interface.implementer(IMailer)
class SESMailer(object):
	"""
	This object does not handle throttling or quata actions;
	see also :mod:`nti.app.bulkemail.process`.
	"""


	def __init__(self):
		pass

	@Lazy
	def sesconn(self):
		return boto.ses.connect_to_region( 'us-east-1' )


	def send(self, fromaddr, toaddrs, message):
		if not isinstance(message, Message): # pragma: no cover
			raise ValueError('Message must be instance of email.message.Message')
		if len(toaddrs) != 1: # pragma: no cover
			raise ValueError("Message con only go to one recipient")
		message = encode_message(message)

		# Send the mail using SES, transforming SESError and known
		# subclasses into something the SMTP-based queue processor knows
		# how to deal with.
		# NOTE: now that we're here, we have the opportunity to de-VERP
		# the fromaddr found in the message, but still use the VERP form
		# in the fromaddr we pass to SES. In this way we can handle bounces
		# with the recipient none-the-wiser. See also :mod:`nti.app.bulkemail.process`
		try:
			self.sesconn.send_raw_email( message, fromaddr, toaddrs[0] )
		except SESAddressBlacklistedError:
			# A permanent error, cause the processor
			# to ditch the message
			raise smtplib.SMTPResponseException( 553, 'Blacklisted address' )

import sys
import logging

class ConsoleApp(_ConsoleApp):

	def __init__(self, argv=None): # pylint: disable=I0011,W0231
		if argv is None:
			argv = sys.argv
		# Bypass the superclass, don't try to construct an SMTP mailer
		self.script_name = argv[0]
		self._process_args(argv[1:])
		self.mailer = SESMailer()
		getattr(self.mailer, 'sesconn')


def run_console(): #pragma NO COVERAGE
	logging.basicConfig(format='%(asctime)s %(message)s')
	app = ConsoleApp()
	app.main()

if __name__ == "__main__": #pragma NO COVERAGE
	run_console()
