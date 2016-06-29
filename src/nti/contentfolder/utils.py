#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import lifecycleevent

from nti.common.file import safe_filename

from nti.contentfolder.interfaces import IRootFolder

from nti.contentfolder.model import ContentFolder

from nti.traversal.traversal import find_interface

class TraversalException(Exception):

	def __init__(self, msg, context=None, segment=None, path=None):
		super(TraversalException, self).__init__(msg)
		self.path = path
		self.context = context
		self.segment = segment

class NotDirectoryException(TraversalException):
	pass

class NotSuchFileException(TraversalException):
	pass

def traverse(current, path=None):
	root = find_interface(current, IRootFolder, strict=False)
	if not path or path == u'/':
		return root
	__traceback_info__ = current, path
	if path.startswith('/'):
		current = root
		path = path[1:]

	path = path.split(u'/')
	if len(path) > 1 and not path[-1]:
		path.pop()

	path.reverse()
	while path:
		segment = path.pop()
		if segment == u'.':
			continue
		if segment == u'..':
			if root != current:
				current = current.__parent__
			continue
		try:
			current = current[segment]
		except KeyError:
			raise NotSuchFileException("Not such file or directory.",
										current, segment, path)
		except TypeError:
			raise NotDirectoryException("Not a directory.",
										current, segment, path)

	return current

def mkdirs(current, path, factory=ContentFolder):
	root = find_interface(current, IRootFolder, strict=False)
	if not path or path == u'/':
		return root
	__traceback_info__ = current, path
	if path.startswith('/'):
		current = root
		path = path[1:]

	path = path.split(u'/')
	if len(path) > 1 and not path[-1]:
		path.pop()

	path.reverse()
	while path:
		segment = path.pop()
		if segment == u'.':
			continue
		if segment == u'..':
			if root != current:
				current = current.__parent__
			continue
		if safe_filename(segment) not in current:
			new_folder = factory()
			new_folder.filename = segment
			new_folder.name = safe_filename(segment)
			lifecycleevent.created(new_folder)
			current[new_folder.name] = new_folder
			current = new_folder
		else:
			current = current[safe_filename(segment)]
	return current
