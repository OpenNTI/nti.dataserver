#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.catalog.interfaces import ICatalog

from nti.dataserver.users.index import CATALOG_NAME

from .delegate import AbstractBulkEmailProcessDelegate

from .interfaces import IBulkEmailProcessDelegate

@interface.implementer(IBulkEmailProcessDelegate)
class _PolicyChangeProcessDelegate(AbstractBulkEmailProcessDelegate):

	subject = 'Updates to NextThought User Agreement and Privacy Policy'

	__name__ = template_name = 'policy_change_email'


	def collect_recipients(self):
		ent_catalog = component.getUtility(ICatalog, name=CATALOG_NAME)

		email_ix = ent_catalog.get( 'email' )
		contact_email_ix = ent_catalog.get( 'contact_email' )

		# It is slightly non-kosher but it is fast and easy to access
		# the forward index for all the email values
		emails = set()
		emails.update( email_ix._fwd_index.keys() )
		emails.update( contact_email_ix._fwd_index.keys() )
		return [{'email': x} for x in emails]

class _PolicyChangeProcessTestingDelegate(_PolicyChangeProcessDelegate):
	"""
	Collects all the emails, but returns a fixed set of test emails.
	"""

	subject = 'TEST - ' + _PolicyChangeProcessDelegate.subject

	__name__ = template_name = 'policy_change_email'

	def collect_recipients( self ):
		recips = super(_PolicyChangeProcessTestingDelegate,self).collect_recipients()
		logger.info( "Real recipient count: %d", len(recips) )
		logger.debug( "%s", recips )
		return [{'email': 'alpha-support@nextthought.com'},
				{'email': 'jason.madden@nextthought.com'},
				{'email': 'grey.allman@nextthought.com'}]
