#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.zope_catalog.catalog import Catalog

from nti.zope_catalog.index import AttributeSetIndex


class ValidatingExternalIdentifiers(object):
    pass


class ExternalIdIndex(AttributeSetIndex):
    pass


class ExternalIdentifierCatalog(Catalog):
    pass
