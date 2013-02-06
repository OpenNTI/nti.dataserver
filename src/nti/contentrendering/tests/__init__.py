#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
import shutil
import tempfile
import StringIO
import io

import zope.component
from pkg_resources import resource_filename

import plasTeX
from plasTeX.TeX import TeX

import nti.contentrendering
from nti.contentrendering import nti_render
from nti.tests import SharedConfiguringTestBase as _ConfiguringTestBase

class ConfiguringTestBase(_ConfiguringTestBase):
	set_up_packages = (nti.contentrendering,)

def buildDomFromString(docString, mkdtemp=False, output_encoding=None, input_encoding=None):
	document = plasTeX.TeXDocument()
	if input_encoding:
		strIO = io.StringIO( docString.decode( input_encoding ) )
		strIO.name = 'temp'
	else:
		strIO = StringIO.StringIO(docString)
		strIO.name = 'temp'

	tex = TeX(document, strIO)
	document.userdata['jobname'] = 'temp'
	document.userdata['working-dir'] = tempfile.gettempdir() if not mkdtemp else tempfile.mkdtemp()
	document.config['files']['directory'] = document.userdata['working-dir']
	document.config.add_section( "NTI" )
	document.config.set( "NTI", 'provider', 'testing' )
	# TODO: Much, but not all of this, is directly copied from nti_render
	document.config.set( 'NTI', 'extra-scripts', '' )
	document.config.set( 'NTI', 'extra-styles', '' )


	#setup default config options we want
	document.config['files']['split-level'] = 1
	document.config['document']['toc-depth'] = sys.maxint # Arbitrary number greater than the actual depth possible
	document.config['document']['toc-non-files'] = True
	# By outputting in ASCII, we are still valid UTF-8, but we use
	# XML entities for high characters. This is more likely to survive
	# through various processing steps that may not be UTF-8 aware
	document.config['files']['output-encoding'] = output_encoding or 'ascii'
	document.config['general']['theme'] = 'NTIDefault'
	document.config['general']['theme-base'] = 'NTIDefault'


	document.userdata['extra_scripts'] = document.config['NTI']['extra-scripts'].split()
	document.userdata['extra_styles'] = document.config['NTI']['extra-styles'].split()


	tex.parse()
	return document

def simpleLatexDocumentText(preludes=(), bodies=()):
	doc = br"""\documentclass[12pt]{article}  """ + b'\n'.join( [unicode(p).encode('utf-8') for p in preludes] ) + 	br"""\begin{document} """
	mathString = b'\n'.join( [unicode(m).encode('utf-8') for m in bodies] )
	doc = doc + b'\n' + mathString + b'\n\\end{document}'
	return doc

class RenderContext(object):

	def __init__( self, latex_tex, dom=None, output_encoding=None, input_encoding=None ):
		self.latex_tex = latex_tex
		self.dom = dom
		self._cwd = None
		self._templates = None
		self.output_encoding = output_encoding
		self.input_encoding = input_encoding

	@property
	def docdir(self):
		return self.dom.config['files']['directory']

	def __enter__(self):
		self._cwd = os.getcwd()
		self._templates = os.environ.get( 'XHTMLTEMPLATES', '' )


		xhtmltemplates = (os.path.join( os.getcwd(), 'Templates' ),
						  #packages_path,
						  # If we fail to instal our templates, and then we try to use our
						  # resource renderer, we find that we get failures due to it
						  # not having setup some things required by the plasTeX default
						  # templates, such as renderer/vectorImager
						  resource_filename( 'nti.contentrendering', 'zpts' ),
						  os.environ.get('XHTMLTEMPLATES', ''))
		os.environ['XHTMLTEMPLATES'] = os.path.pathsep.join( xhtmltemplates)

		if self.dom is None:
			self.dom = buildDomFromString( self.latex_tex, True, output_encoding=self.output_encoding, input_encoding=self.input_encoding )
		os.chdir( self.docdir )
		import nti.contentrendering.plastexids
		nti.contentrendering.plastexids.patch_all()
		nti_render.setupChameleonCache()
		return self

	def __exit__( self, exc_type, exc_value, traceback ):
		os.environ['XHTMLTEMPLATES'] = self._templates
		os.chdir( self._cwd )
		shutil.rmtree( self.docdir )
