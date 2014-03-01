#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" """
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import has_length


import unittest

from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText

import nti.contentrendering

def _simpleLatexDocument(maths):
    return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.picins}',),
                                    bodies=maths )

class TestPicins(unittest.TestCase):

	def test_picskip(self):
		example = br"""
		\picskip{0}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('picskip'), has_length( 0 ) )

	def test_parpic(self):
		example = br"""
		\parpic(0pt,2.8in)[r][t]{\includegraphics{test}}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('parpic'), has_length( 1 ) )
