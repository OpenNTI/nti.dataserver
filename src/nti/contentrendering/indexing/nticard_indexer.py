#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Whoosh NTI card indexer.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
from datetime import datetime

from zope import component
from zope import interface

from nti.contentindexing.whooshidx import NTICARD_IDXNAME_PREDIX
from nti.contentindexing.whooshidx.interfaces import IWhooshNTICardIndexer
from nti.contentindexing.whooshidx.interfaces import IWhooshNTICardSchemaCreator

from nti.contentprocessing import get_content_translation_table

from ._utils import get_attribute
from ._utils import get_node_content

from .content_utils import sanitize_content

from .common_indexer import BasicWhooshIndexer

@interface.implementer(IWhooshNTICardIndexer)
class WhooshNTICardIndexer(BasicWhooshIndexer):

	def get_schema(self, name='en'):
		creator = component.getUtility(IWhooshNTICardSchemaCreator, name=name)
		return creator.create()

	def _get_attribute(self, node, attr):
		result = get_attribute(node, attr)
		return result or u''

	def _get_nticard_info(self, topic, node):
		type_ = get_attribute(node, 'type')
		if type_ == u'application/vnd.nextthought.nticard':
			result = {}
			content = get_node_content(node)
			result['type'] = self._get_attribute(node, 'data-type')
			result['href'] = self._get_attribute(node, 'data-href')
			result['title'] = self._get_attribute(node, 'data-title')
			result['ntiid'] = self._get_attribute(node, 'data-ntiid')
			result['creator'] = self._get_attribute(node, 'data-creator')
			for obj in node.iterchildren():
				if 	obj.tag == 'span' and \
					get_attribute(obj, 'class') == 'description':
					content = get_node_content(obj)
				elif obj.tag == 'param':
					name = get_attribute(obj, 'name')
					value = get_attribute(obj, 'value')
					if name and not result.get(name, None) and value:
						result[name] = value
			result['content'] = unicode(content) if content else u''
			return result
		return None

	def _sanitize(self, table, text):
		text = text.translate(table) if table and text else text
		return text

	def index_card_entry(self, writer, containerId, info, lang=u'en'):
		table = get_content_translation_table(lang)
		ntiid = info.get('ntiid')
		title = info.get('title')
		if not ntiid or not title:
			return False

		try:
			href = info.get('href', u'')
			content = info.get('content', u'')
			target_ntiid = info.get('target_ntiid', u'')
			type_ = self._sanitize(table, info.get('type', u''))
			creator = self._sanitize(table, info.get('creator', u''))
			title = sanitize_content(title, table=table)
			content = sanitize_content(content, table=table)
			last_modified = datetime.fromtimestamp(time.time())
			writer.add_document(containerId=containerId,
								type=type_,
								href=href,
								ntiid=ntiid,
								title=title,
								creator=creator,
								content=content,
								target_ntiid=target_ntiid,
								quick=unicode("%s %s" % (title, content)),
								last_modified=last_modified)
			return True
		except Exception:
			writer.cancel()
			raise

	def get_index_name(self, book, indexname=None):
		indexname = super(WhooshNTICardIndexer, self).get_index_name(book, indexname)
		indexname = NTICARD_IDXNAME_PREDIX + indexname
		return indexname

	def process_topic(self, idxspec, topic, writer, language='en'):
		result = {}
		containerId = unicode(topic.ntiid)
		for n in topic.dom(b'object'):
			info = self._get_nticard_info(topic, n)
			if info:
				ntiid = info.get('ntiid')
				if ntiid:
					result[ntiid] = (info, containerId)
		return result

	def _index_cards(self, cards, writer, lang='en'):
		count = 0
		for _, data in cards.items():
			info, containerId = data
			if self.index_card_entry(writer, containerId, info, lang):
				count += 1
		return count

	def process_book(self, idxspec, writer, lang='en'):
		cards = {}
		toc = idxspec.book.toc
		def _loop(topic):
			m = self.process_topic(idxspec, topic, writer, lang)
			cards.update(m)
			for t in topic.childTopics:
				_loop(t)
		_loop(toc.root_topic)

		result = self._index_cards(cards, writer, lang)
		return result

_DefaultWhooshNTICardIndexer = _WhooshNTICardIndexer = WhooshNTICardIndexer
