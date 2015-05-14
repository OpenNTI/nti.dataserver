#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import unicode_literals, print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from cStringIO import StringIO

from zope.file.upload import nameFinder
import zope.file.interfaces as zfile_interfaces

import zope.file.file as zfile
zfile = zfile

import plone.namedfile.file as nfile
import plone.namedfile.utils as nutils
import plone.namedfile.interfaces as nfile_interfaces

from zope import component

from zope.interface import interfaces

from zope.mimetype.interfaces import IMimeTypeGetter

from nti.common.property import alias

def _patch():
	# First, make plone's IFile extend zope's IFile. zope's IFile
	# declares the streaming interfaces open and openDetached while
	# plone's only declares the buffered 'data' interface, though
	# the blob-versions implement open and openDetached
	if nfile_interfaces.IFile.__iro__ != (nfile_interfaces.IFile, interfaces.Interface,):
		raise ImportError("Internals of plone.namedfile have changed")

	nfile_interfaces.IFile.__bases__ = (zfile_interfaces.IFile,)

	# They are almost compatible, with a few minor differences we
	# fix up here.

	# size as a property (zope) vs getSize() (plone)
	nfile.NamedFile.size = property(nfile.NamedFile.getSize)
	# is already in the blob versions
	assert hasattr(nfile.NamedBlobFile, 'size')

	# zfile is an ILocation. We say that __name__ is always the same
	# as filename...this is tricky because __name__ on a type means
	# the type name; only instances can see what's in the type's
	# __dict__ (and we can't assign to it). So we resort to sticking
	# in a base class.
	# TODO: Rethink that, it's probably not right. __name__ is the
	# name within the container; it may initially be based on
	# the filename, but they are probably different
	class _Base(object):
		__name__ = alias('filename')
	assert len(nfile.NamedFile.__bases__) == 1
	nfile.NamedFile.__bases__ += (_Base,)
	assert len(nfile.NamedBlobFile.__bases__) == 1
	nfile.NamedBlobFile.__bases__ += (_Base,)

	nfile.NamedFile.__parent__ = None
	nfile.NamedBlobFile.__parent__ = None

	# zfile is IContentTypeAware, plonefile declares 'contentType'
	nfile.NamedFile.mimeType = alias('contentType')
	nfile.NamedBlobFile.mimeType = alias('contentType')
	# and it needs parameters (actually, zfile doesn't get that
	# right either)
	nfile.NamedFile.parameters = {}  # true this is unsafe but they are supposed to be read-only
	nfile.NamedBlobFile.parameters = {}

	# plone's non-blob-based files don't have open/openDetached,
	# so we fake it
	def _open(self, mode='r'):
		return StringIO(self.data)
	nfile.NamedFile.open = _open
	nfile.NamedFile.openDetached = _open

	func_globals = getattr(nutils.get_contenttype, 'func_globals')
	func_globals['component'] = component
	func_globals['nameFinder'] = nameFinder
	func_globals['IMimeTypeGetter'] = IMimeTypeGetter
	nutils.get_contenttype.__code__ = _get_contenttype.__code__

# plone's guessing of content types is very limited compared to what zope does;
# let's use that instead. But many places have already imported it
# statically by name, so swizzle out the code
def _get_contenttype(file=None, filename=None, default='application/octet-stream'):
	file_type = getattr(file, 'contentType', None)
	if file_type:
		return file_type
	filename = getattr(file, 'filename', filename)

	mimeTypeGetter = component.getUtility(IMimeTypeGetter)
	mimeType = mimeTypeGetter(data=getattr(file, 'data', None),
							  content_type=None,
							  name=nameFinder(filename))
	return mimeType or default

def patch():
	pass

_patch()
del _patch
