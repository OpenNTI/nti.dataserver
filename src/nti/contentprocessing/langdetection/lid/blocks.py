# -*- coding: utf-8 -*-
"""
Categorize unicode characters by the code block in which they are found.

Copyright (c) 2008, Kent S Johnson 
https://pypi.python.org/pypi/guess-language

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import re
from bisect import bisect_left

def _load_blocks():
	""""
	Load Blocks.txt.
	Create and return two parallel lists. One has the start and end points for
	codepoint ranges, the second has the corresponding block name.
	"""
	# Expects our version of Blocks.txt to be in the same dir as this file
	blocks_path = os.path.join(os.path.dirname(__file__), 'Blocks.txt')
	names = []
	endpoints = []
	splitter = re.compile(r'^(....)\.\.(....); (.*)$')
	with open(blocks_path, "r") as src:
		for line in src:
			if line.startswith('#'):
				continue
			line = line.strip()
			if not line:
				continue

			m = splitter.match(line)
			if not m:
				continue

			start = int(m.group(1), 16)
			end = int(m.group(2), 16)
			name = m.group(3)

			endpoints.append(start)
			endpoints.append(end)

			names.append(name)
			names.append(name)

	return endpoints, names

_endpoints, _names = _load_blocks()

def unicode_block(c):
	""" 
	Returns the name of the unicode block containing c
	c must be a single character.
	"""
	ix = bisect_left(_endpoints, ord(c))
	return _names[ix]
