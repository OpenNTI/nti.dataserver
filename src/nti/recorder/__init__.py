#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.zope_catalog.interfaces import IMetadataCatalog

from .index import CATALOG_NAME

from .record import get_transactions
from .record import remove_transaction_history

def get_recorder_catalog():
	return component.queryUtility(IMetadataCatalog, name=CATALOG_NAME)
