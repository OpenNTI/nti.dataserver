#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# Disable pylint warning about "too many methods" on the Command subclasses,
# and "deprecated string" module
#pylint: disable=R0904,W0402

from plasTeX.Base import chapter

class mathcountschapter( chapter ):
	args = '* [ toc ] title img'
