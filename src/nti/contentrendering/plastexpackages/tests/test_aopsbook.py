#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" """
from __future__ import print_function, unicode_literals, absolute_import


# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


from hamcrest import assert_that, is_, has_length

import unittest

from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText

import nti.contentrendering


def _simpleLatexDocument(maths):
    return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.aopsbook}',),
                                    bodies=maths )

class TestAopsBook(unittest.TestCase):

	def test_challProb(self):
		example = br"""
		\chall
		In Park School grade, 33 students and 12 teachers like none of these sports. \hints~\hint{cCount:3circles.1}, \hint{cCount:3circles.2}
		"""

		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('hint'), has_length( 2 ) )

		#check that we don't have a comma in between hints
		hints = dom.getElementsByTagName('hint')
		assert_that(hints[0].nodeName, is_( hints[0].nextSibling.nodeName ))
		#Check if we don't have a trailing comma at the end.
		assert_that( dom.textContent.strip(), is_("In Park School grade, 33 students and 12 teachers like none of these sports."))

	def test_multipleTrailingComma(self):
		example = br"""
		\challhard
		Arbitrary content goes here. \hints~\hint{cCount:3circles.1},~\hint{cCount:3circles.2}, \hint{cCount:3circles.3}
		"""

		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('hint'), has_length( 3 ) )

		#Check if we don't have a trailing comma at the end.
		assert_that( dom.textContent.strip(), is_("Arbitrary content goes here."))

	def test_oneHint(self):
		example = br"""
		\challhard
		Arbitrary content goes here. \hints~\hint{cCount:3circles.1}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('hint'), has_length( 1 ) )

		#Check if we don't have a trailing comma at the end.
		assert_that( dom.textContent.strip(), is_("Arbitrary content goes here."))


	def test_part(self):
		example = br"""
		\begin{parts}
		\part part a.
		\part part b.
		\part part c.
		\part part d.
		\part part e.
		\part part f.
		\end{parts}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('part'), has_length( 6 ) )

	def test_part_no_title(self):
		example = br"""
		\begin{parts}
		\part part a.
		\part part b.
		\part part c.
		\part part d.
		\part part e.
		\part[]
		\end{parts}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('part'), has_length( 6 ) )

	def test_part_title(self):
		example = br"""
		\begin{parts}
		\part part a.
		\part part b.
		\part part c.
		\part part d.
		\part part e.
		\part[Something]
		\end{parts}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('part'), has_length( 6 ) )

	def test_lcm(self):
		example = br"""
		$\lcm[45, 60, 75]$
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('lcm'), has_length( 1 ) )

	def test_davesuglyhack(self):
		example = br"""
		\davesuglyhack
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('davesuglyhack'), has_length( 1 ) )
