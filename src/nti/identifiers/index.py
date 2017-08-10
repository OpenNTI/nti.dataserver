#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.zope_catalog.catalog import Catalog

from nti.zope_catalog.index import AttributeSetIndex

class ValidatingExternalIdentifiers(object):
    pass

class ExternalIdIndex(AttributeSetIndex):
    pass

class ExternalIdentifierCatalog(Catalog):
    pass

