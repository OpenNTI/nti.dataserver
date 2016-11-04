#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search common functions.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import six
from collections import Iterable

def is_all_query(query):
	mo = re.search('([\?\*])', query)
	return mo is not None and mo.start(1) == 0

def to_list(data):
	if isinstance(data, six.string_types):
		data = [data]
	elif isinstance(data, list):
		pass
	elif isinstance(data, Iterable):
		data = list(data)
	elif data is not None:
		data = [data]
	return data
