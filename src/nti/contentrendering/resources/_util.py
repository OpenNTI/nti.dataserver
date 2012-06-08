#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import os, os.path
import shutil
from hashlib import sha1

class _ExternalHasher(object):
	"""
	Provides methods to create ASCII hashes
	for use as paths on the filesystem or composite keys
	in a dictionary.
	"""

	def digestKeys(self, toDigests):
		"""
		Hashes all the values in `toDigests` after turning them into strings
		and sorting them. The sorting is a convenience to the client, allowing
		multiple clients to be composed together in the creation of a key,
		or to use datastructures such as a set whose iteration order may
		change over time.
		"""
		skeys = sorted([str(x) for x in toDigests])
		dkey = ' '.join(skeys)

		return self.digest(dkey)

	def digest(self, toDigest):
		toDigest = toDigest.encode('ascii', 'backslashreplace')
		return sha1( toDigest ).hexdigest()

digester = _ExternalHasher()

def copy(source, dest, debug=True):

	if not os.path.exists(os.path.dirname(dest)):
		os.makedirs(os.path.dirname(dest))
	try:
		shutil.copy2(source, dest)
	except OSError:
		shutil.copy(source, dest)
