#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A hack to help us ensure that we are loading and monkey-patching
the entire system before Pyramid loads: loading Pyramid's ``pserve``
loads many Pyramid modules, including :mod:`pyramid.traversal`, which
in turn loads :mod:`repoze.lru` and allocates real, non-recursive
thread locks. These are not compatible with gevent and eventually
lead to a hang if we re-enter a greenlet that wants to acquire one
of these locks while a previous greenlet already has it.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# Note that we must not import *anything* before the patch
from nti.monkey import gevent_patch_on_import
gevent_patch_on_import.patch()

from nti.traversal import monkey as traversing_patch_on_import
traversing_patch_on_import.patch()
del traversing_patch_on_import

logger = __import__('logging').getLogger(__name__)

from nti.monkey import relstorage_patch_all_on_import
relstorage_patch_all_on_import.patch()

from nti.monkey import webob_cookie_escaping_patch_on_import
webob_cookie_escaping_patch_on_import.patch()

from nti.monkey import random_seed_patch_on_import
random_seed_patch_on_import.patch()

import sys
from pkg_resources import load_entry_point, get_distribution

def main():
	# We used to monkey patch some things in 1.3. We no longer
	# do now that we expect to be on 1.5. Check this.
	pyramid_dist = get_distribution('pyramid')
	if pyramid_dist and pyramid_dist.has_version():
		assert pyramid_dist.version.startswith('1.7')

	sys.exit(
		load_entry_point('pyramid', 'console_scripts', 'pserve')()
	)
