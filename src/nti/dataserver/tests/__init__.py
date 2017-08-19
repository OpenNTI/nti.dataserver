#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


# for export
from  nti.testing import matchers
has_attr = matchers.has_attr
provides = matchers.provides
implements = matchers.implements
