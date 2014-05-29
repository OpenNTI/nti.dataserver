#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Package to hold modules corresponding to packages that can
be used in latex documents.

A best practice is to make these modules importable directly (as if this
directory was on the PYTHONPATH). This allows the use of \usepackage{foo}
rather than \usepackage{nti.contentrendering.plastexpackages.foo}.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
