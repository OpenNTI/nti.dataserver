#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import base64

try:
	from Crypto.Cipher import XOR
except:
	XOR = None

DEFAULT_PASSPHRASE = base64.b64decode('TjN4dFRoMHVnaHQhIUM=')

def make_ciphertext(plaintext, passphrase=DEFAULT_PASSPHRASE):
	if XOR is not None:
		cipher = XOR.new(passphrase)
		encoded = cipher.encrypt(plaintext)
	else:
		encoded = plaintext
	result = base64.b64encode(encoded)
	return result
	
def get_plaintext(ciphertext, passphrase=DEFAULT_PASSPHRASE):
	result = base64.b64decode(ciphertext)
	if XOR is not None:
		cipher = XOR.new(passphrase)
		result = cipher.decrypt(result)
	return result
