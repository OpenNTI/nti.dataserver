#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" """
from __future__ import print_function, unicode_literals, absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import has_length

import unittest

from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText


import nti.contentrendering


def _simpleLatexDocument(maths):
    return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.amsopn}',),
                                    bodies=maths )

class TestAMS(unittest.TestCase):
	def test_DeclareMathOperator(self):
		example = br"""
		\DeclareMathOperator*{\lcm}{lcm}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('DeclareMathOperator'), has_length( 1 ) )
