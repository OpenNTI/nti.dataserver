#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of the :class:`nti.mailer.interfaces.IVERP` protocol.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from .interfaces import IEmailAddressable
from .interfaces import IVERP
from zope.security.interfaces import IPrincipal

import rfc822
import itsdangerous

from nti.appserver.policies.site_policies import find_site_policy


def _make_signer(default_key='$Id$'):

	# TODO: Break these dependencies
	from nti.appserver.interfaces import IApplicationSettings

	settings = component.getGlobalSiteManager().queryUtility(IApplicationSettings) or {}
	# XXX Reusing the cookie secret, we should probably have our own
	secret_key = settings.get('cookie_secret', default_key)

	signer = itsdangerous.Signer(secret_key, salt='email recipient')
	return signer

def _find_default_realname():
	"""
	Called when the given fromaddr does not have a realname portion.
	We would prefer to use whatever is in the site policy, if there
	is one, otherwise we have a hardcoded default.
	"""
	realname = None
	policy, policy_name = find_site_policy()
	if policy is not None and policy_name and getattr(policy, 'DEFAULT_EMAIL_SENDER', None):
		realname, _ = rfc822.parseaddr(policy.DEFAULT_EMAIL_SENDER)
		if realname is not None:
			realname = realname.strip()

	return realname or "NextThought"

def verp_from_recipients( fromaddr, recipients, request=None ):

	realname, addr = rfc822.parseaddr(fromaddr)
	if not realname and not addr:
		raise ValueError("Invalid fromaddr", fromaddr)
	if '+' in addr:
		raise ValueError("Addr should not already have a label", fromaddr)

	if not realname:
		realname = _find_default_realname()

	# We could special case the common case of recpients of length
	# one if it is a string: that typically means we're sending to the current
	# principal (though not necessarily so we'd have to check email match).
	# However, instead, I just want to change everything to send something
	# adaptable to IEmailAddressable instead.

	adaptable_to_email_addressable = [x for x in recipients
									  if IEmailAddressable(x,None) is not None]
	principals = {IPrincipal(x, None) for x in adaptable_to_email_addressable}
	principals.discard(None)

	principal_ids = {x.id for x in principals}
	if principal_ids:
		principal_ids = ','.join(principal_ids)
		# mildly encode them; this is just obfuscation.
		# Do that after signing to be sure we wind up with
		# something rfc822-safe
		# First, get bytes to avoid any default-encoding
		principal_ids = principal_ids.encode('utf-8')
		# now sign
		signer = _make_signer()
		principal_ids = signer.sign(principal_ids)
		# finally obfuscate in a url/email safe way
		principal_ids = itsdangerous.base64_encode(principal_ids)

		local, domain = addr.split('@')
		addr = local + '+' + principal_ids + '@' + domain

	return rfc822.dump_address_pair( (realname, addr) )

def principal_ids_from_verp(fromaddr, request=None, default_key=None):
	if not fromaddr or '+' not in fromaddr:
		return ()

	_, addr = rfc822.parseaddr(fromaddr)
	if '+' not in addr:
		return ()

	signed_and_encoded = addr.split('+', 1)[1].split('@')[0]
	signed_and_decoded = itsdangerous.base64_decode(signed_and_encoded)

	signer = _make_signer() if not default_key else _make_signer(default_key=default_key)
	try:
		pids = signer.unsign(signed_and_decoded)
	except itsdangerous.BadSignature:
		return ()
	else:
		return pids.split(',')

interface.moduleProvides(IVERP)
