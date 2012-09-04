#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# Import NOW to ensure we get the right monkey patches
# Importing here, when we start from pserve/supervisor, lets
# us be sure that the transaction manager and zope.component get the
# right threading bases and we don't have to use our fancy patched classes
# (which do work, but this is safer)
import nti.dataserver
