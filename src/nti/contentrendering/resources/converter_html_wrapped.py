# -*- coding: utf-8 -*-
"""
A resource converter the copies a resource into the resource system and then wraps 
it inside of an HTML PRE block.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import datetime
import codecs
import isodate
import os
import tempfile

import nti.contentrendering.resources as resources

from ._util import copy
from . import converters

_RESOURCE_TYPE = 'html_wrapped'

class _HTMLWrapper(object):

	def __init__(self, ntiid, in_file, out_file):
		self.filename = out_file
		self.data = {}
		self.data['ntiid'] = ntiid
		self.data['title'] = os.path.basename(in_file)
		self.data['last-modified'] = isodate.datetime_isoformat(datetime.datetime.utcnow())

		# Read the input file
		with codecs.open( in_file, 'rb', 'utf-8') as f:
			self.data['content'] = f.read()

	def write_to_file(self):
		template =u"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html lang="en">
	<head>
		<meta http-equiv="last-modified" content="%s" />
		<meta name="NTIID" content="%s" />
		<meta name="generator" content="NextThought" />
		<meta http-equiv="content-type" tal:attributes="content string:text/html;; charset=utf-8" />
		<title>%s</title>
	</head>
	<body id="NTIContent">
		<div class="page-contents">
			<h3>%s</h3>
			<pre>%s</pre>
		</div>
	</body>
</html>
"""
		# Write the HTML output
		data = template % (self.data['last-modified'], self.data['ntiid'], self.data['title'], self.data['title'], self.data['content'])
		with codecs.open( self.filename, 'wb', 'utf-8') as f:
			f.write(data)

class HTMLWrappedBatchConverterDriver(object):

	fileExtension = '.html'
	resourceType = _RESOURCE_TYPE

	def __init__(self):
		self.tempdir = tempfile.mkdtemp()

	def _convert_unit(self, unit):
		unit_path = unit.attributes['src']
		ext = os.path.splitext(unit_path)[1]
		resource_path = tempfile.mkstemp(suffix=ext,dir=self.tempdir)[1]

		plain = resources.Resource()
		plain.path = resource_path
		plain.resourceType = 'raw'
		plain.qualifiers = ('raw',)
		plain.source = unit.source
		copy(unit_path, plain.path)

		html = resources.Resource()
		html.path = resource_path + self.fileExtension
		html.resourceType = self.resourceType
		html.qualifiers = ('wrapped',)
		html.source = unit.source
		ntiid = unit.ntiid if hasattr(unit,'ntiid') else unit.id
		_HTMLWrapper(ntiid, plain.path, html.path).write_to_file()

		return [plain, html]

	def convert_batch(self, content_units):	
		# Here we need to wrap the input inside of a PRE block of a stand alone HTML file.
		resources = []
		for unit in content_units:
			resources.extend(self._convert_unit(unit))
		return resources

class HTMLWrappedBatchConverter(converters.AbstractContentUnitRepresentationBatchConverter):
	"""
	Converts by embedding the specified file in the body of a HTML file inside of a PRE block.
	"""

	resourceType = _RESOURCE_TYPE

	def _new_batch_converter_driver(self, *args, **kwargs):
		return HTMLWrappedBatchConverterDriver()

ResourceGenerator = HTMLWrappedBatchConverter
ResourceSetGenerator = HTMLWrappedBatchConverterDriver

from zope.deprecation import deprecated
deprecated(['ResourceGenerator', 'ResourceSetGenerator'], 'Prefer the new names in this module')
