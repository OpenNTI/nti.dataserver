#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_, has_length
from hamcrest import has_property
from hamcrest import instance_of
from hamcrest import equal_to
from nose.tools import assert_raises

from plasTeX.Base.LaTeX.Crossref import label

from nti.contentrendering.tests import buildDomFromString as _buildDomFromString
from nti.contentrendering.tests import simpleLatexDocumentText


from nti.contentrendering.plastexpackages.graphicx import includegraphics
from nti.contentrendering.plastexpackages.ntilatexmacros import ntiincludevideo, ntivideo
from nti.contentrendering.plastexpackages.ntislidedeck import ntislide, ntislidedeck, ntislidedeckref, ntislidevideo, _timeconvert

def _simpleLatexDocument(maths):
	return simpleLatexDocumentText( preludes=(br'\usepackage{nti.contentrendering.plastexpackages.ntilatexmacros}',
											  br'\usepackage{nti.contentrendering.plastexpackages.ntislidedeck}'),
									bodies=maths )

def test_timeconvert():
	assert_that( _timeconvert( '25' ), is_( 25 ) )
	assert_that( _timeconvert( '1:25' ), is_( 85 ) )
	assert_that( _timeconvert( '1:0:25' ), is_( 3625 ) )

	with assert_raises(ValueError) as e:
		_timeconvert( '1:95' )

	assert_that( e.exception.args[0], is_('Invalid time in 1:95'))

	with assert_raises(ValueError) as e:
		_timeconvert( '1:1:95' )

	assert_that( e.exception.args[0], is_('Invalid time in 1:1:95'))

	with assert_raises(ValueError) as e:
		_timeconvert( '1:95:25' )

	assert_that( e.exception.args[0], is_('Invalid time in 1:95:25'))

	with assert_raises(ValueError) as e:
		_timeconvert( '1:95:95' )

	assert_that( e.exception.args[0], is_('Invalid time in 1:95:95'))

def test_ntislidedeck():
	example = br"""
\begin{ntislidedeck}[creator=NTI]
\label{myslidedeck}
\caption{Test Presentation}
\includegraphics[width=106px,height=60px]{test}
Test Presentation.
\end{ntislidedeck}
"""
	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

	# Check that the DOM has the expected structure
	assert_that( dom.getElementsByTagName('ntislidedeck'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('ntislidedeck')[0], is_( ntislidedeck ) )

	# Check that the ntislidevideo object has the expected children
	elem = dom.getElementsByTagName('ntislidedeck')[0]
	__traceback_info__ = elem.childNodes
	assert_that( elem.childNodes[1], is_( label ) )
	assert_that( elem.childNodes[3], is_( ntislidedeck.caption ) )
	assert_that( elem.childNodes[5], is_( includegraphics ) )

def test_ntislidevideo_legacy():
	example = br"""
\begin{ntislidedeck}[creator=NTI]
\label{myslidedeck}
\caption{Test Presentation}
\includegraphics[width=106px,height=60px]{test}
Test Presentation.
\end{ntislidedeck}

\begin{ntislidevideo}
\label{video1}
\ntiincludevideo{//www.youtube.com/embed/goKHhz9RfGo?html5=1&rel=0}
\ntislidedeckref{myslidedeck}
\end{ntislidevideo}
"""
	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

	# Check that the DOM has the expected structure
	assert_that( dom.getElementsByTagName('ntislidevideo'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('ntislidevideo')[0], is_( ntislidevideo ) )

	# Check that the ntislidevideo object has the expected children
	elem = dom.getElementsByTagName('ntislidevideo')[0]
	__traceback_info__ = elem.childNodes
	assert_that( elem.childNodes[0], is_( label ) )
	assert_that( elem.childNodes[2], is_( ntiincludevideo ) )
	video = elem.childNodes[2]

	# Check that the ntislidevido object has the expected attributes
	assert_that( elem, has_property( 'id' ) )
	assert_that( elem, has_property( 'title' ) )
	assert_that( elem, has_property( 'creator' ) )
	assert_that( elem, has_property( 'slidedeck' ) )
	assert_that( elem, has_property( 'thumbnail' ) )

	# Check that the attributes have the expected values
	assert_that( elem.title, equal_to( 'No Title' ) )
	assert_that( elem.creator, equal_to( 'Unknown' ) )
	assert_that( elem.thumbnail, equal_to( video.attributes['thumbnail'] ) )

def test_ntislidevideo_unified():
	example = br"""
\begin{ntislidedeck}[creator=NTI]
\label{myslidedeck}
\caption{Test Presentation}
\includegraphics[width=106px,height=60px]{test}
Test Presentation.
\end{ntislidedeck}

\begin{ntislidevideo}
\label{video1}
\begin{ntivideo}[creator=NTI]
\caption{My Video}
\ntivideosource{youtube}{goKHhz9RfGo}
\end{ntivideo}
\ntislidedeckref{myslidedeck}
\end{ntislidevideo}
"""
	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

	# Check that the DOM has the expected structure
	assert_that( dom.getElementsByTagName('ntislidevideo'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('ntislidevideo')[0], is_( ntislidevideo ) )

	# Check that the ntislidevideo object has the expected children
	elem = dom.getElementsByTagName('ntislidevideo')[0]
	__traceback_info__ = elem.childNodes
	assert_that( elem.childNodes[0], is_( label ) )
	assert_that( elem.childNodes[2], is_( ntivideo ) )
	video = elem.childNodes[2]

	# Check that the ntislidevido object has the expected attributes
	assert_that( elem, has_property( 'id' ) )
	assert_that( elem, has_property( 'title' ) )
	assert_that( elem, has_property( 'creator' ) )
	assert_that( elem, has_property( 'slidedeck' ) )
	assert_that( elem, has_property( 'thumbnail' ) )

	thumbnail = video.getElementsByTagName( 'ntivideosource' )[0].thumbnail
	# Check that the attributes have the expected values
	assert_that( elem.title, equal_to( video.title ) )
	assert_that( elem.creator, equal_to( video.creator ) )
	assert_that( elem.thumbnail, equal_to( thumbnail ) )

def test_ntislide():
	example = br"""
\begin{ntislidedeck}[creator=NTI]
\label{myslidedeck}
\caption{Test Presentation}
\includegraphics[width=106px,height=60px]{test}
Test Presentation.
\end{ntislidedeck}

\begin{ntislidevideo}
\label{video1}
\ntiincludevideo{//www.youtube.com/embed/goKHhz9RfGo?html5=1&rel=0}
\ntislidedeckref{myslidedeck}
\end{ntislidevideo}

\begin{ntislide}
\label{slide1}
\ntislidetitle{Test Slide}
\ntislidenumber{101}
\ntislideimage[width=640px]{test}
\ntislidevideoref[start=0:00,end=1:25]{video1}
\ntislidedeckref{myslidedeck}
\begin{ntislidetext}
Title Slide
\end{ntislidetext}
\end{ntislide}
"""
	dom = _buildDomFromString( _simpleLatexDocument( (example,) ) )

	# Check that the DOM has the expected structure
	assert_that( dom.getElementsByTagName('ntislidevideo'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('ntislidevideo')[0], is_( ntislidevideo ) )
	assert_that( dom.getElementsByTagName('ntislide'), has_length( 1 ) )
	assert_that( dom.getElementsByTagName('ntislide')[0], is_( ntislide ) )

	# Check that the ntislidevideo object has the expected children
	elem = dom.getElementsByTagName('ntislide')[0]
	__traceback_info__ = elem.childNodes
	assert_that( elem.childNodes[0], instance_of( label ) )
	assert_that( elem.childNodes[2], instance_of( ntislide.ntislidetitle ) )
	assert_that( elem.childNodes[4], instance_of( ntislide.ntislidenumber ) )
	assert_that( elem.childNodes[6], instance_of( ntislide.ntislideimage ) )
	assert_that( elem.childNodes[8], instance_of( ntislide.ntislidevideoref ) )
	assert_that( elem.childNodes[10], instance_of( ntislidedeckref ) )
	assert_that( elem.childNodes[12], instance_of( ntislide.ntislidetext ) )
	slide_title = elem.childNodes[2]
	slide_number = elem.childNodes[4]

	# Check that the ntislidevido object has the expected attributes
	assert_that( elem, has_property( 'id' ) )
	assert_that( elem, has_property( 'title' ) )
	assert_that( elem, has_property( 'slidenumber' ) )
	assert_that( elem, has_property( 'slideimage' ) )
	assert_that( elem, has_property( 'slidevideo' ) )

	# Check that the attributes have the expected values
	assert_that( elem.title, equal_to( slide_title.attributes['title'] ) )
	assert_that( elem.slidenumber, equal_to( slide_number.attributes['number'] ) )
	assert_that( elem.slideimage, equal_to( elem.childNodes[6] ) )
	assert_that( elem.slidevideo, equal_to( elem.childNodes[8] ) )
