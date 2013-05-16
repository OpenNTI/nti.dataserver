#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZODB 4.0.0b2 has a bug decoding OIDs for transformation to bytes, at least under python2
with an ASCII default codec.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from ZODB.blob import BushyLayout

KNOWN_BAD_OID = b'>\xf1<0\xe9Q\x99\xf0'

try:
	BushyLayout().oid_to_path( KNOWN_BAD_OID )
except UnicodeDecodeError:
	#https://github.com/zopefoundation/ZODB/commit/e7d8ca7229998146f79e1f90302ae6486bc95a60
	# changed `str(oid)` to oid.decode(), which, if the oid is already bytes, and it should
	# be already bytes, tries to decode with the default encoding, which is often
	# ascii

	import binascii # hexlify takes bytes and returns bytes on py2 and py3
	from ZODB._compat import ascii_bytes
	import os.path  # os.path.sep is a bytes on py2 and py3
	def oid_to_path(self, oid):
		directories = []
		# Create the bushy directory structure with the least significant byte
		# first
		for byte in ascii_bytes(oid):
			directories.append(
				'0x%s' % binascii.hexlify(byte))
		return os.path.sep.join(directories)

	BushyLayout.oid_to_path = oid_to_path

def patch():
	pass
