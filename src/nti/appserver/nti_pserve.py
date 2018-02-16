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
from pkg_resources import load_entry_point


def main():
    sys.exit(
        load_entry_point('pyramid', 'console_scripts', 'pserve')()
    )


if __name__ == '__main__':
    sys.exit(main())
