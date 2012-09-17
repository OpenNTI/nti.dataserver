#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Objects for working with the RFC2397 ``data`` URL scheme::

	data:[<MIME-type>][;charset=<encoding>][;base64],<data>

The encoding is indicated by ``;base64``. If it's present the data is
encoded as base64. Without it the data (as a sequence of octets) is
represented using ASCII encoding for octets inside the range of safe
URL characters and using the standard %xx hex encoding of URLs for
octets outside that range. If ``<MIME-type>`` is omitted, it defaults
to ``text/plain;charset=US-ASCII``. (As a shorthand, the type can be
omitted but the charset parameter supplied.)

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from urllib import unquote, quote
from base64 import b64decode, b64encode

# Originally inspired by http://code.google.com/p/python-mom/source/browse/mom/net/scheme/dataurl.py?

def decode(data_url):
	"""
	Decodes a data URL into raw bytes and metadata.

	:param data_url:
		The data url string.
		If a mime-type definition is missing in the metadata,
		"text/plain;charset=US-ASCII" will be used as default mime-type.
	:returns:
		A 2-tuple::
			(bytes, mime_type_string)
		The mime_type string will not be parsed. See :func:`zope.contenttype.parse.parse` for that.
	"""


	metadata, encoded = data_url.rsplit( b",", 1)
	_, metadata = metadata.split( b"data:", 1 )
	metadata_parts = metadata.rsplit( b";", 1 )
	if metadata_parts[-1] == b"base64":
		_decode = b64decode
		metadata_parts = metadata_parts[:-1]
	else:
		_decode = unquote
	if not metadata_parts or not metadata_parts[0]:
		metadata_parts = ("text/plain;charset=US-ASCII",)
	mime_type = metadata_parts[0]
	raw_bytes = _decode(encoded)
	return raw_bytes, mime_type

_def_charset = b'US-ASCII',
_marker = object()
def encode(raw_bytes,
		   mime_type=b'text/plain',
		   charset=_marker,
		   encoder="base64"):
	"""
	Encodes raw bytes into a data URL scheme string.

	:param raw_bytes: Raw bytes
	:param mime_type: The mime type, e.g. b"text/css" or b"image/png". Default b"text/plain".
	:param charset:	b"utf-8" if you want the data URL to contain a b"charset=utf-8"
		component. Default b'US-ASCII'. This does not mean however, that your
		raw_bytes will be encoded by this function. You must ensure that
		if you specify, b"utf-8" (or anything else) as the encoding, you
		have encoded your raw data appropriately.

		.. note:: This function employs a heuristic to know when to default this
			parameter (for example, it is not used for image mime types). To be absolutely
			sure, set it explicitly (None meaning not to use it).
	:param encoder:	"base64" or None.
	:returns: Data URL byte string
	"""
	if not isinstance( raw_bytes, str ):
		raise TypeError("only raw bytes can be encoded")

	if encoder == "base64":
		_encode = b64encode
		codec = b";base64,"
	else:
		# We want ASCII bytes.
		_encode = lambda data: quote(data).encode('ascii')
		codec = b","
	mime_type = mime_type or b""

	if charset is _marker:
		if mime_type.startswith( 'text/' ):
			charset = _def_charset
		else:
			charset = None

	charset = b";charset=" + charset if charset else b""
	encoded = _encode(raw_bytes)
	return b''.join( (b"data:", mime_type, charset, codec, encoded) )
