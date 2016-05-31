#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A hack to help us ensure that we are loading and monkey-patching
the desired parts of zodbconvert before it gets started.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.monkey import relstorage_patch_all_on_import
relstorage_patch_all_on_import.patch()

import sys

from pkg_resources import load_entry_point

def main():
	sys.exit(
		load_entry_point('relstorage', 'console_scripts', 'zodbconvert')()
	)
