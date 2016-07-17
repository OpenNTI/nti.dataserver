#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A hack to help us ensure that we are loading and monkey-patching
the desired parts of ZEO before it gets started.

Note that we are not making ZEO use gevent; it is allowed to use real
threads and blocking IO. The developers of ZEO claim that it does
efficiently use multiple cores in that way (at least with
FileStorage). However, we do force relstorage to use
umysqldb drivers for consistency with non-ZEO uses (umysql seems to handle
disconnections better---fewer ``<class '_mysql_exceptions.OperationalError'>: (2006, 'MySQL server has gone away')``)
We do make relstorage work with newer releases of
persistent and make it compatible with zlibstorage.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.monkey import patch_relstorage_umysqldb_on_import
patch_relstorage_umysqldb_on_import.patch()

# NOTE: Not importing patch_all, don't want gevent
# (XXX: Except we probably do, definitely under pypy.)

import sys

from pkg_resources import load_entry_point, get_distribution

def main():
	zeo_dist = get_distribution( 'ZEO' )
	if zeo_dist and zeo_dist.has_version():
		assert zeo_dist.version.startswith( '4.' )

	sys.exit(
		load_entry_point('ZEO', 'console_scripts', 'runzeo')()
	)
