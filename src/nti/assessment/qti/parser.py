# -*- coding: utf-8 -*-
"""
QTI Parser

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from lxml import etree
from io import BytesIO

from .vocabulary import get_qti_object_factory

def _localname(e):
	tag = etree.QName(e.tag)
	return tag.localname

def parser(source):
	source = BytesIO(source) if not hasattr(source, 'read') else source
	tree = etree.parse(source)
	root = tree.getroot()

	def _process_element(e):
		qti_element = None
		name = _localname(e)
		factory = get_qti_object_factory(name)
		if factory is not None:
			qti_element = factory()

			# set tail text
			text = e.text.strip() if e.text else None
			if text:
				qti_element._text = text

			tail = e.tail.strip() if e.tail else None
			if tail:
				qti_element._tail = tail

			# process attribtes
			for k, v in e.attrib.items():
				qti_element.set_attribute(k, v)

			# process children
			for child in e:
				child_qti = _process_element(child)
				if child_qti is not None:
					qti_element.set_element(child_qti)
		else:
			logger.debug("Unrecognized element '%s'" % name)

		return qti_element

	result = _process_element(root)
	return result

