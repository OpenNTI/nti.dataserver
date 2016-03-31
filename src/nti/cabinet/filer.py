	#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import pickle
import shutil
import mimetypes

from zope import interface

from nti.cabinet.interfaces import ISourceFiler

from nti.cabinet.mixins import SourceFile, SourceProxy
from nti.cabinet.mixins import ReferenceSourceFile

from nti.common.random import generate_random_hex_string

def _add_types():
	mimetypes.add_type('text/html', '.shtml')
	mimetypes.add_type('text/mathml', '.mml')
	mimetypes.add_type('text/x-component', '.htc')
	mimetypes.add_type('image/x-jng', '.jng')
	mimetypes.add_type('application/java-archive', '.war')
	mimetypes.add_type('application/java-archive', '.ear')
	mimetypes.add_type('application/x-cocoa', '.cco')
	mimetypes.add_type('application/x-java-archive-diff', '.jardiff');
	mimetypes.add_type('application/x-makeself', '.run')
	mimetypes.add_type('application/x-perl', ',pm')
	mimetypes.add_type('application/x-redhat-package-manager', '.rpm')
	mimetypes.add_type('application/x-sea', '.sea')
	mimetypes.add_type('application/x-tcl', '.tcl')
	mimetypes.add_type('application/x-tcl', '.tk')
	mimetypes.add_type('application/x-x509-ca-cert', '.pem')
	mimetypes.add_type('video/3gpp', '.3gpp')
_add_types()
del _add_types

def transfer_to_storage_file(source, target):
	if hasattr(source, 'read'):
		target.data = source.read()
	elif hasattr(source, 'data'):
		target.data = source.data
	else:
		target.data = source

	if getattr(source, 'contentType', None):
		target.contentType = source.contentType

def transfer_to_native_file(source, target):
	with open(target, "wb") as fp:
		if hasattr(source, 'read'):
			fp.write(source.read())
		elif hasattr(source, 'data'):
			fp.write(source.data)
		else:
			fp.write(source)

@interface.implementer(ISourceFiler)
class DirectoryFiler(object):

	def __init__(self, path, native=True):
		self.native = native
		self.path = self.prepare(path) if path else None

	def prepare(self, path):
		path = os.path.expanduser(path)
		if not os.path.exists(path):
			os.makedirs(path)
		elif not os.path.isdir(path):
			raise IOError("%s is not directory", path)
		return path

	def reset(self, path=None):
		path = self.path if not path else path
		if path:
			path = os.path.expanduser(path)
			shutil.rmtree(path, True)
			return True
		return False

	def _get_unique_file_name(self, path, key):
		separator = '_'
		key_noe, ext = os.path.splitext(key)
		while True:
			s = generate_random_hex_string(6)
			newtext = "%s%s%s%s" % (key_noe, separator, s, ext)
			newtext = os.path.join(path, newtext)
			if not os.path.exists(newtext):
				break
		return newtext

	def new_storage_file(self, key, out_dir, reference=False):
		if reference:
			target = ReferenceSourceFile(out_dir, key)
		else:
			target = SourceFile(key)
		return target

	def save(self, key, source, contentType=None, bucket=None, overwrite=False,
			 relative=True, reference=False, **kwargs):
		contentType = contentType or u'application/octet-stream'
		key = os.path.split(key)[1]  # proper name

		# get output directory
		out_dir = os.path.join(self.path, bucket) if bucket else self.path
		out_dir = os.path.normpath(out_dir)
		if not out_dir.startswith(self.path):
			raise IOError("Invalid bucket name")

		if not os.path.exists(out_dir):
			os.makedirs(out_dir)

		if not overwrite:
			out_file = self._get_unique_file_name(out_dir, key)
		else:
			out_file = os.path.join(out_dir, key)

		if not self.native:
			target = self.new_storage_file(key, out_dir, reference)
			transfer_to_storage_file(source, target)
			target.contentType = contentType or target.contentType
			target.close()
			with open(out_file, "wb") as fp:
				pickle.dump(target, fp, pickle.HIGHEST_PROTOCOL)
		else:
			transfer_to_native_file(source, out_file)

		if relative:
			out_file = os.path.relpath(out_file, self.path)
		return out_file

	def get(self, key):
		if not key.startswith(self.path):
			key = os.path.join(self.path, key)
		key = os.path.normpath(key)
		if not key.startswith(self.path) or not os.path.exists(key):
			return None

		if not self.native:
			with open(key, "rb") as fp:
				result = pickle.load(fp)
		else:
			name = os.path.split(key)[1]
			contentType = mimetypes.guess_type(name.lower())[0]
			result = SourceProxy(open(key, "rb"), name,
								 contentType=contentType,
								 length=os.stat(key).st_size)
		return result

	def remove(self, key):
		result = self.get(key)
		if result is not None:
			if hasattr(result, 'remove'):
				result.remove()
			else:
				if not key.startswith(self.path):
					key = os.path.join(self.path, key)
				os.remove(key)
			return True
		return False

	def contains(self, key, bucket=None):
		if bucket:
			if not bucket.startswith(self.path):
				bucket = os.path.join(self.path, bucket)
				bucket = os.path.normpath(bucket)
			key = os.path.join(bucket, key)
		elif not key.startswith(self.path):
			key = os.path.join(self.path, key)
			key = os.path.normpath(key)
		result = key.startswith(self.path) and os.path.exists(key)
		return result

	def list(self, bucket=None):
		path = os.path.join(self.path, bucket) if bucket else self.path
		path = os.path.normpath(path)
		if not path.startswith(self.path):
			raise IOError("Invalid bucket name")
		result = tuple(os.listdir(path))
		return result

	def is_bucket(self, key):
		if not key.startswith(self.path):
			key = os.path.join(self.path, key)
		key = os.path.normpath(key)
		if not key.startswith(self.path) or not os.path.exists(key):
			return False
		return os.path.isdir(key)
