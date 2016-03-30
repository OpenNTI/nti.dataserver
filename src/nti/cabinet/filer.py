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

from zope import interface

from nti.cabinet.interfaces import ISourceFiler

from nti.cabinet.mixins import SourceFile
from nti.cabinet.mixins import ReferenceSourceFile

from nti.common.random import generate_random_hex_string

def transfer(source, target):
	if hasattr(source, 'read'):
		target.data = source.read()
	elif hasattr(source, 'data'):
		target.data = source.data
	else:
		target.data = source

	if getattr(source, 'contentType', None):
		target.contentType = source.contentType

@interface.implementer(ISourceFiler)
class DirectoryFiler(object):

	def __init__(self, path):
		self.path = self.reset(path) if path else None

	def reset(self, path):
		path = os.path.expanduser(path)
		if not os.path.exists(path):
			os.makedirs(path)
		elif not os.path.isdir(path):
			raise IOError("%s is not directory", path)
		return path

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

		if reference:
			target = ReferenceSourceFile(out_dir, key)
		else:
			target = SourceFile(key)
		transfer(source, target)
		target.contentType = contentType or target.contentType
		target.close()

		with open(out_file, "wb") as fp:
			pickle.dump(target, fp, pickle.HIGHEST_PROTOCOL)
		if relative:
			out_file = os.path.relpath(out_file, self.path)
		return out_file

	def get(self, key):
		if not key.startswith(self.path):
			key = os.path.join(self.path, key)
		key = os.path.normpath(key)
		if not key.startswith(self.path) or not os.path.exists(key):
			return None
		with open(key, "rb") as fp:
			result = pickle.load(fp)
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
