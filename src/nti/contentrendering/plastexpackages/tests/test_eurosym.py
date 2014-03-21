# -*- coding: utf-8 -*-
""" """
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import is_


import unittest


from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText


def _simpleLatexDocument(maths):
    return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.eurosym}',),
                                    bodies=maths )

class TestEUR(unittest.TestCase):

	def test_eur_1(self):
		example = br"""
		\EUR{10}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('EUR'), has_length( 1 ) )
		element = dom.getElementsByTagName('EUR')[0]
		assert_that( element.childNodes, has_length( 1 ) )
		assert_that( element.childNodes[0].textContent, is_( u'\u20AC\u202F10' ) )

	def test_eur_2(self):
		example = br"""
		\EUR{}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('EUR'), has_length( 1 ) )
		element = dom.getElementsByTagName('EUR')[0]
		assert_that( element.childNodes, has_length( 1 ) )
		assert_that( element.childNodes[0].textContent, is_( u'\u20AC\u202F' ) )


class TestEuro(unittest.TestCase):

	def test_euro(self):
		example = br"""
		\euro 10
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )
		assert_that( dom.getElementsByTagName('euro'), has_length( 1 ) )
		element = dom.getElementsByTagName('euro')[0]
		assert_that( element.textContent, is_( u'\u20AC' ) )


