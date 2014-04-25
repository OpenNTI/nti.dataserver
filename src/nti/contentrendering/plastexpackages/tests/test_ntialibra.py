#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

# from nti.contentrendering.plastexpackages.graphicx import includegraphics
from nti.contentrendering.plastexpackages.ntialibra import ntisequenceitem, ntisequence

from nti.contentrendering.tests import simpleLatexDocumentText
from nti.contentrendering.tests import buildDomFromString as _buildDomFromString

def _simpleLatexDocument(maths):
	return simpleLatexDocumentText(
					preludes=(br'\usepackage{nti.contentrendering.plastexpackages.ntilatexmacros}',
						 	  br'\usepackage{nti.contentrendering.plastexpackages.ntialibra}'),
					bodies=maths)

class TestNTIAlibra(unittest.TestCase):

	def test_ntintisequence(self):
		example = br"""
			\begin{ntisequence}[creator=NTI]
				\includegraphics[width=106px,height=60px]{test}
				\begin{ntisequenceitem}
					 foo
				\end{ntisequenceitem}
				\begin{ntisequenceitem}
					\includegraphics[width=106px,height=60px]{test3}
				\end{ntisequenceitem}
			\end{ntisequence}
		"""
		dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

		# Check that the DOM has the expected structure
		assert_that(dom.getElementsByTagName('ntisequence'), has_length(1))
		assert_that(dom.getElementsByTagName('ntisequence')[0], is_(ntisequence))

		# Check that the ntisequence object has the expected children
		elem = dom.getElementsByTagName('ntisequence')[0]
		assert_that(elem.childNodes[2], is_(ntisequenceitem))
		assert_that(elem.childNodes[4], is_(ntisequenceitem))
