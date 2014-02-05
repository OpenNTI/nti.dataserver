#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Simply sends an event to generate an email invoice

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import argparse

from zope import component
from zope.event import notify

from nti.dataserver.utils import run_with_dataserver

from nti.store import invitations
from nti.store import interfaces as store_interfaces

def _generate_invoice(transaction, site=None):

	from pyramid.testing import setUp as psetUp
	from pyramid.testing import DummyRequest

	request = DummyRequest()
	config = psetUp(registry=component.getGlobalSiteManager(),
					request=request,
					hook_zca=False)
	config.setup_registry()
	if site:
		request.headers['origin'] = \
			'http://' + site if not site.startswith('http') else site
		request.possible_site_names = \
			 (site if not site.startswith('http') else site[7:],)

	purchase = invitations.get_purchase_by_code(transaction)
	if purchase is None or not store_interfaces.IPurchaseAttempt.providedBy(purchase):
		logger.error('Purchase attempt not found')
		return 2
	elif not purchase.has_succeeded():
		logger.error('Purchase was not successfull')
		return 3

	notify(store_interfaces.PurchaseAttemptSuccessful(purchase, request=request))
	return 0

def main(args=None):
	arg_parser = argparse.ArgumentParser(description="Generates an invoice")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('transaction', help="The transaction code")
	arg_parser.add_argument('--site', dest='site', help='request SITE')
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	args = arg_parser.parse_args(args=args)

	env_dir = args.env_dir
	conf_packages = () if not args.site else ('nti.appserver',)

	function = lambda: _generate_invoice(args.transaction, args.site)
	result = run_with_dataserver(environment_dir=env_dir,
								 xmlconfig_packages=conf_packages,
								 verbose=args.verbose,
								 function=function)
	return result

if __name__ == '__main__':
	code = main()
	sys.exit(code)
