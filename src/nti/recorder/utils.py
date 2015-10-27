#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zlib
import pickle
from io import BytesIO

def compress(obj):
	bio = BytesIO()
	pickle.dump(obj, bio)
	bio.seek(0)
	result = zlib.compress(bio.read())
	return result

def decompress(source):
	data = zlib.decompress(source)
	bio = BytesIO(data)
	bio.seek(0)
	result = pickle.load(bio)
	return result
