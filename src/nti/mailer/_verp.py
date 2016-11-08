#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of the :class:`nti.mailer.interfaces.IVERP` protocol.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import rfc822

import itsdangerous

from zope import component
from zope import interface

from zope.security.interfaces import IPrincipal

# TODO: break this dep
from nti.appserver.policies.site_policies import find_site_policy

from nti.mailer.interfaces import IVERP
from nti.mailer.interfaces import IEmailAddressable

def _get_signer_secret(default_secret="$Id$"):

	# TODO: Break these dependencies
	from nti.appserver.interfaces import IApplicationSettings

	settings = component.getGlobalSiteManager().queryUtility(IApplicationSettings) or {}
	# XXX Reusing the cookie secret, we should probably have our own
	secret_key = settings.get('cookie_secret', default_secret)

	return secret_key

import zlib
import struct

class _InsecureAdlerCRC32Digest(object):
	"""
	Just enough of a hashlib-like object to satisfy
	itsdangerous, producing a 32-bit integer checksum
	instead of a real 128 or 256 bit checksum.
	This is specifically NOT cryptographically secure,
	but for purposes of \"not looking stupid\" we've decided
	that email account security doesn't matter.
	"""

	# These aren't documented and are reverse engineered

	digest_size = 4  # size of the output
	block_size = 64  # ???

	def __init__(self, init=b''):
		self.val = init

	def copy(self):
		return self.__class__(self.val)

	def update(self, val):
		self.val += val

	def digest(self):
		crc = zlib.adler32(self.val)
		return struct.pack('i', crc)

def _make_signer(default_key='$Id$',
				 salt='email recipient',
				 digest_method=_InsecureAdlerCRC32Digest):
	"""
	Note that the default separator, '.' may appear in principal ids.
	"""
	secret_key = _get_signer_secret(default_secret=default_key)
	signer = itsdangerous.Signer(secret_key,
								 salt=salt,
								 digest_method=digest_method)
	return signer

def _find_default_realname(request=None):
	"""
	Called when the given fromaddr does not have a realname portion.
	We would prefer to use whatever is in the site policy, if there
	is one, otherwise we have a hardcoded default.
	"""
	realname = None
	policy, policy_name = find_site_policy(request=request)
	if policy is not None and policy_name and getattr(policy, 'DEFAULT_EMAIL_SENDER', None):
		realname, _ = rfc822.parseaddr(policy.DEFAULT_EMAIL_SENDER)
		if realname is not None:
			realname = realname.strip()

	return realname or "NextThought"

def __make_signer(default_key, **kwargs):
	return _make_signer(**kwargs) if not default_key else _make_signer(default_key=default_key, **kwargs)

import urllib

def _sign(signer, principal_ids):
	"""
	Given a signer, and a byte-string of principal ids, return
	a signed value, as lightly obfuscated as possible, to satisfy
	concerns about \"looking stupid\".

	Note that this value easily exposes the principal ID in readable fashion,
	giving someone in possession of the email both principal ID and registered
	email address. Watch out for phishing attacks.
	"""

	sig = signer.get_signature(principal_ids)
	# The sig is always already base64 encoded, in the
	# URL/RFC822 safe fashion.
	principal_ids = urllib.quote(principal_ids)

	return principal_ids + signer.sep + sig

def realname_from_recipients(fromaddr, recipients, request=None):
	realname, addr = rfc822.parseaddr(fromaddr)
	if not realname and not addr:
		raise ValueError("Invalid fromaddr", fromaddr)
	if not realname:
		realname = _find_default_realname(request=request)

	return rfc822.dump_address_pair((realname, addr))

def verp_from_recipients(fromaddr, 
						 recipients,
						 request=None,
						 default_key=None):

	realname, addr = rfc822.parseaddr(realname_from_recipients(fromaddr, recipients, request=request))

	# We could special case the common case of recipients of length
	# one if it is a string: that typically means we're sending to the current
	# principal (though not necessarily so we'd have to check email match).
	# However, instead, I just want to change everything to send something
	# adaptable to IEmailAddressable instead.

	adaptable_to_email_addressable = [x for x in recipients
									  if IEmailAddressable(x, None) is not None]
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
		signer = __make_signer(default_key)
		principal_ids = _sign(signer, principal_ids)

		local, domain = addr.split('@')
		# Note: we may have a local address that already has a label '+'.
		# The principal ids with '+' should now be url quoted away. This
		# ensures we want the last '+' on parsing.
		addr = local + '+' + principal_ids + '@' + domain

	return rfc822.dump_address_pair((realname, addr))

def principal_ids_from_verp(fromaddr,
							request=None,
							default_key=None):
	if not fromaddr or '+' not in fromaddr:
		return ()

	_, addr = rfc822.parseaddr(fromaddr)
	if '+' not in addr:
		return ()

	signer = __make_signer(default_key)

	# Split on our last '+' to allow user defined labels.
	signed_and_encoded = addr.rsplit(b'+', 1)[1].split(b'@')[0]
	encoded_pids, sig = signed_and_encoded.rsplit(signer.sep, 1)
	decoded_pids = urllib.unquote(encoded_pids)

	signed = decoded_pids + signer.sep + sig

	try:
		pids = signer.unsign(signed)
	except itsdangerous.BadSignature:
		return ()
	else:
		return pids.split(',')

interface.moduleProvides(IVERP)
