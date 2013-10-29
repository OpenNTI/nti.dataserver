# -*- coding: utf-8 -*-
"""
Content search module.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# monkey patch
from  . import monkey
monkey.patch()

from .constants import indexable_type_names
from .common import videotimestamp_to_datetime
from .constants import ugd_indexable_type_names
from .constants import vtrans_prefix, nticard_prefix

def get_indexable_types():
	return indexable_type_names

def get_ugd_indexable_types():
	return ugd_indexable_type_names

