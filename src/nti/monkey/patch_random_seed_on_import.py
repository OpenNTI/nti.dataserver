#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python versions prior to 2.7.7 do a very poor job seeding
the random number space. This backport the algorithm from 2.7.7.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys

def _do_patch():
	from random import _hexlify
	from random import _urandom
	from random import Random

	def seed(self, a=None):
		if a is None:
			try:
				# Seed with enough bytes to span the 19937 bit
				# state space for the Mersenne Twister
				a = long(_hexlify(_urandom(2500)), 16)
			except NotImplementedError:
				import time
				a = long(time.time() * 256) # use fractional seconds

		super(Random, self).seed(a)
		self.gauss_next = None

	# Fix new instances
	Random.seed = seed

	# But by importing, we caused the creation of an
	# instance that got seeded; in fact, it may have
	# been imported before us and even had the convenience
	# methods cached as class or module level constants
	# so we can't just replace them. We thus provide a wrapper
	from random import _inst
	def inst_seed(a=None):
		seed(_inst, a)

	# Match some attributes of an instancemethod
	inst_seed.im_class = Random
	inst_seed.im_func = inst_seed.__func__ = seed
	inst_seed.im_self = inst_seed.__self__ = _inst
	inst_seed() # re seed with good values

	import random
	random.seed = inst_seed

def _patch():
	if sys.version_info < (2,7,7):
		_do_patch()

def patch():
	pass

_patch()
