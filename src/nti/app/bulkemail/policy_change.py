#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component

from zope.catalog.interfaces import ICatalog

from nti.dataserver.users import index as user_index

from .process import AbstractBulkEmailProcessLoop

class _PolicyChangeProcess(AbstractBulkEmailProcessLoop):

	subject = 'Updates to NextThought User Agreement and Privacy Policy'

	template_name = 'policy_change_email'

	def initialize(self):
		"""
		Prep the process for starting. Preflight it, then collect all the
		recipients needed.
		"""

		self.preflight_process()
		logger.info( "Beginning process for %s", self.template_name )

		self.metadata.startTime = time.time()
		self.metadata.status = 'Started'
		self.metadata.save()

		recips = self.collect_recipients()
		logger.info( "Collected %d recipients", len(recips) )
		self.add_recipients( *recips )

	def collect_recipients(self):
		ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)

		email_ix = ent_catalog.get( 'email' )
		contact_email_ix = ent_catalog.get( 'contact_email' )

		# It is slightly non-kosher but it is fast and easy to access
		# the forward index for all the email values
		emails = set()
		emails.update( email_ix._fwd_index.keys() )
		emails.update( contact_email_ix._fwd_index.keys() )
		return [{'email': x} for x in emails]

class _PolicyChangeProcessTesting(AbstractBulkEmailProcessLoop):
	"""
	Collects all the emails, but returns a fixed set of test emails.
	"""

	subject = 'TEST - ' + _PolicyChangeProcess.subject

	template_name = 'policy_change_email'

	def collect_recipients( self ):
		recips = super(_PolicyChangeProcessTesting,self).collect_recipients()
		logger.info( "Real recipient count: %d", len(recips) )
		logger.debug( "%s", recips )
		return [{'email': 'alpha-support@nextthought.com'},
				{'email': 'jason.madden@nextthought.com'},
				{'email': 'grey.allman@nextthought.com'}]
