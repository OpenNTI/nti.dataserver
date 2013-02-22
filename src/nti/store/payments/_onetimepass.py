# -*- coding: utf-8 -*-
"""
onetimepass module is designed to work for one-time passwords 

https://github.com/tadeck/onetimepass/blob/master/onetimepass/__init__.py

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import hmac
import time
import base64
import struct
import hashlib

def is_possible_token(token):
	"""
	Determines if given value is acceptable as a token. Used when validating
	tokens.

	Currently allows only numeric tokens no longer than 6 chars.

	:param token: token value to be checked
	:type token: int or str
	:return: True if can be a candidate for token, False otherwise
	:rtype: bool

	>>> is_possible_token(123456)
	True
	>>> is_possible_token('123456')
	True
	>>> is_possible_token('abcdef')
	False
	>>> is_possible_token('12345678')
	False
	"""
	return str(token).isdigit() and len(str(token)) <= 6

def get_hotp(secret, intervals_no, as_string=False, casefold=True):
	"""
	Get HMAC-based one-time password on the basis of given secret and
	interval number.

	:param secret: the base32-encoded string acting as secret key
	:type secret: str
	:param intervals_no: interval number used for getting different tokens, it
		is incremented with each use
	:type intervals_no: int
	:param as_string: True if result should be padded string, False otherwise
	:type as_string: bool
	:param casefold: True (default), if should accept also lowercase alphabet
	:type casefold: bool
	:return: generated HOTP token
	:rtype: int or str

	>>> get_hotp('MFRGGZDFMZTWQ2LK', intervals_no=1)
	765705
	>>> get_hotp('MFRGGZDFMZTWQ2LK', intervals_no=2)
	816065
	>>> get_hotp('MFRGGZDFMZTWQ2LK', intervals_no=2, as_string=True)
	'816065'
	"""
	try:
		key = base64.b32decode(secret, casefold=casefold)
	except (TypeError):
		raise TypeError('Incorrect secret')
	msg = struct.pack(b">Q", intervals_no)
	hmac_digest = hmac.new(key, msg, hashlib.sha1).digest()
	o = ord(hmac_digest[19]) & 15
	token_base = struct.unpack(b">I", hmac_digest[o:o + 4])[0] & 0x7fffffff
	token = token_base % 1000000
	if as_string:
		return '{:06d}'.format(token)
	else:
		return token

def get_totp(secret, as_string=False):
	"""Get time-based one-time password on the basis of given secret and time.

	:param secret: the base32-encoded string acting as secret key
	:type secret: str
	:param as_string: True if result should be padded string, False otherwise
	:type as_string: bool
	:return: generated TOTP token
	:rtype: int or str

	>>> get_hotp('MFRGGZDFMZTWQ2LK', int(time.time())//30) == \
		get_totp('MFRGGZDFMZTWQ2LK')
	True
	>>> get_hotp('MFRGGZDFMZTWQ2LK', int(time.time())//30) == \
		get_totp('MFRGGZDFMZTWQ2LK', as_string=True)
	False
	"""
	interv_no = int(time.time()) // 30
	return get_hotp(secret, intervals_no=interv_no, as_string=as_string)

def valid_hotp(token, secret, last=1, trials=1000):
	"""Check if given token is valid for given secret. Return interval number
	that was successful, or False if not found.

	:param token: token being checked
	:type token: int or str
	:param secret: secret for which token is checked
	:type secret: str
	:param last: last used interval (start checking with next one)
	:type last: int
	:param trials: number of intervals to check after 'last'
	:type trials: int
	:return: interval number, or False if check unsuccessful
	:rtype: int or bool

	>>> secret = 'MFRGGZDFMZTWQ2LK'
	>>> valid_hotp(713385, secret, last=1, trials=5)
	4
	>>> valid_hotp(865438, secret, last=1, trials=5)
	False
	>>> valid_hotp(713385, secret, last=4, trials=5)
	False
	"""
	if not is_possible_token(token):
		return False

	for i in xrange(last + 1, last + trials + 1):
		if get_hotp(secret=secret, intervals_no=i) == int(token):
			return i
	return False

def valid_totp(token, secret):
	"""Check if given token is valid time-based one-time password for given
	secret.

	:param token: token which is being checked
	:type token: int or str
	:param secret: secret for which the token is being checked
	:type secret: str
	:return: True, if is valid token, False otherwise
	:rtype: bool

	>>> secret = 'MFRGGZDFMZTWQ2LK'
	>>> token = get_totp(secret)
	>>> valid_totp(token, secret)
	True
	>>> valid_totp(token+1, secret)
	False
	>>> token = get_totp(secret, as_string=True)
	>>> valid_totp(token, secret)
	True
	>>> valid_totp(token+'1', secret)
	False
	"""
	return is_possible_token(token) and int(token) == get_totp(secret)
