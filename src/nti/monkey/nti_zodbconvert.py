#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A hack to help us ensure that we are loading and monkey-patching
the desired parts of zodbconvert before it gets started.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_patch_all_on_import

relstorage_patch_all_on_import.patch()

from . import python_persistent_bugs_patch_on_import
python_persistent_bugs_patch_on_import.patch()


import sys
from pkg_resources import load_entry_point


def main():
	sys.exit(
		load_entry_point('relstorage', 'console_scripts', 'zodbconvert')()
	)
