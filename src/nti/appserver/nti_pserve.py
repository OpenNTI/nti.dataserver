#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A hack to help us ensure that we are loading and monkey-patching
the entire system before pyramid loads: loading pyramid's pserve
loads many pyramid modules, including pyramid.traversal, which
in turn loads repoze.lru and allocates real, non-recursive
thread locks. These are not compatible with gevent and eventually
lead to a hang if we re-enter a greenlet that wants to acquire one
of these locks while a previous greenlet already has it.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from nti.monkey import gevent_patch_on_import
gevent_patch_on_import.patch()

import sys
from pkg_resources import load_entry_point

def main():
    sys.exit(
        load_entry_point('pyramid', 'console_scripts', 'pserve')()
    )
