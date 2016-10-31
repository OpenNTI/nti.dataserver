#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# CS:20150303 make sure this module is not deleted b/c we need the 
# deprecation moved as wold whoosh indexes are pickled with this 
# namespace
import zope.deprecation
zope.deprecation.moved('nti.contentindexing.whooshidx.schemas')
