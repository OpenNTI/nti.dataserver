#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" """
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import has_entry
import unittest

import plasTeX
from plasTeX.Base.LaTeX.Crossref import label

from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText

from nti.contentrendering.transforms.trans_caption import transform as captionTransform

def _simpleLatexDocument(maths):
	return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.graphicx}',
						  br'\usepackage{nti.contentrendering.plastexpackages.ntilatexmacros}'),
					bodies=maths )

def test_captionTransform():
	example = br"""
\begin{figure*}
\includegraphics{sample}
\caption*{Caption 1}
\end{figure*}

\begin{figure*}
\ntiincludeannotationgraphics{sample}
\caption*{Caption 2}
\end{figure*}

\begin{figure*}
\ntiincludenoannotationgraphics{sample}
\caption*{Caption 3}
\end{figure*}

\begin{table}
\begin{tabular}{ll}
& \\
\end{tabular}
\caption*{Caption4}
\end{table}
	"""

	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

	captions = dom.getElementsByTagName('caption')
	assert_that( captions, has_length(4))

	#run the transform
	captionTransform( dom )

	assert_that( captions[0].style, has_entry( 'display', 'none' ) )
	assert_that( captions[1].style, has_entry( 'display', 'none' ) )
	assert_that( captions[2].style, has_entry( 'display', 'none' ) )
	assert_that( captions[3].style, is_not(has_entry( 'display', 'none' )) )
