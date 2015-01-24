#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import inspect

def caller_name(skip=2):
	"""
	Get a name of a caller in the format module.class.method
	
	`skip` specifies how many levels of stack to skip while getting caller
	name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.
	   
	An empty string is returned if skipped levels exceed stack height
	
	adapted from https://gist.github.com/techtonik/2151727
	"""
	stack = inspect.stack()
	start = 0 + skip
	if len(stack) < start + 1:
		return ''

	name = []
	parentframe = stack[start][0]	
	module = inspect.getmodule(parentframe)
	if module:
		name.append(module.__name__)
	# detect classname
	if 'self' in parentframe.f_locals:
		# I don't know any way to detect call from the object method
		# there seems to be no way to detect static method call - it will
		# be just a function call
		name.append(parentframe.f_locals['self'].__class__.__name__)
	codename = parentframe.f_code.co_name
	if codename != '<module>':  # top level usually
		name.append( codename ) # function or a method
	del parentframe
	return ".".join(name)
