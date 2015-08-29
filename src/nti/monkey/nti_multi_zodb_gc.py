#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: nti_multi_zodb_gc.py 69226 2015-07-20 15:11:13Z carlos.sanchez $
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from . import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import sys

from pkg_resources import load_entry_point

def main():
    # Not a threaded process, no need to check for switches
    sys.setcheckinterval(100000)
    ec = load_entry_point('zc.zodbdgc', 'console_scripts', 'multi-zodb-gc')()
    sys.exit(ec)

if __name__ == '__main__':
    main()
