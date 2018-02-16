#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A hack to help us ensure that we are loading and monkey-patching
the entire system before Pyramid loads

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# NOTE: We must not import *anything* before the patch
from nti.monkey import patch_nti_pserve_on_import
patch_nti_pserve_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import sys
from pkg_resources import load_entry_point, get_distribution


def main():
    # We used to monkey patch some things in 1.3. We no longer
    # do now that we expect to be on 1.5. Check this.
    pyramid_dist = get_distribution('pyramid')
    if pyramid_dist and pyramid_dist.has_version():
        assert pyramid_dist.version.startswith('1.8') \
            or pyramid_dist.version.startswith('1.9')

    sys.exit(
        load_entry_point('pyramid', 'console_scripts', 'pserve')()
    )


if __name__ == '__main__':
    sys.exit(main())
