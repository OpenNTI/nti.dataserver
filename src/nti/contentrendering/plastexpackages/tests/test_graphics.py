#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" """
from __future__ import print_function, unicode_literals


from hamcrest import assert_that
from hamcrest import has_length


import unittest

from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText

def _simpleLatexDocument(maths):
    return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.graphics}',),
                                    bodies=maths )

class TestGraphics(unittest.TestCase):

	def test_DeclareGraphicsRule(self):
		example = br"""
		\DeclareGraphicsRule{*}{mps}{*}{}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('DeclareGraphicsRule'), has_length( 1 ) )
