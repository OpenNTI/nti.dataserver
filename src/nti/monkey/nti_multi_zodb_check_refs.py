#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. note:: You must have the MySQL-python driver installed, as we
	cannot monkey patch to use umysqldb due to errors. See
	that patch for details.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.monkey import patch_relstorage_all_except_gevent_on_import
patch_relstorage_all_except_gevent_on_import.patch()

import sys
from pkg_resources import load_entry_point

def main():
	ec = load_entry_point('zc.zodbdgc', 'console_scripts', 'multi-zodb-check-refs')()
	sys.exit(ec)

if __name__ == '__main__':
	main()
