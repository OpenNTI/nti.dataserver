# -*- coding: utf-8 -*-
"""
Whoosh NTI card indexer.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time
from datetime import datetime

from zope import component
from zope import interface

from nti.contentprocessing import get_content_translation_table

from nti.contentsearch import nticard_prefix
from nti.contentsearch import interfaces as search_interfaces

from . import _node_utils as node_utils
from . import _content_utils as content_utils
from . import interfaces as cridxr_interfaces
from ._common_indexer import _BasicWhooshIndexer

@interface.implementer(cridxr_interfaces.IWhooshNTICardIndexer)
class _WhooshNTICardIndexer(_BasicWhooshIndexer):

	def get_schema(self, name='en'):
		creator = component.getUtility(search_interfaces.IWhooshNTICardSchemaCreator, name=name)
		return creator.create()

	def _get_attribute(self, node, attr):
		result = node_utils.get_attribute(node, attr)
		return result or u''

	def _get_nticard_info(self, topic, node):
		type_ = node_utils.get_attribute(node, 'type')
		if type_ == u'application/vnd.nextthought.nticard':
			result = {}
			content = node_utils.get_node_content(node)
			result['type'] = self._get_attribute(node, 'data-type')
			result['href'] = self._get_attribute(node, 'data-href')
			result['title'] = self._get_attribute(node, 'data-title')
			result['ntiid'] = self._get_attribute(node, 'data-ntiid')
			result['creator'] = self._get_attribute(node, 'data-creator')
			for obj in node.iterchildren():
				if obj.tag == 'span' and node_utils.get_attribute(obj, 'class') == 'description':
					content = node_utils.get_node_content(obj)
				elif obj.tag == 'param':
					name = node_utils.get_attribute(obj, 'name')
					value = node_utils.get_attribute(obj, 'value')
					if name and not result.get(name, None) and value:
						result[name] = value
			result['content'] = unicode(content) if content else u''
			return result
		return None

	def _sanitize(self, table, text):
		text = text.translate(table) if table and text else text
		return text

	def index_card_entry(self, writer, containerId, info, language=u'en'):
		table = get_content_translation_table(language)
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
			title = content_utils.sanitize_content(title, table=table)
			content = content_utils.sanitize_content(content, table=table)
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
		indexname = super(_WhooshNTICardIndexer, self).get_index_name(book, indexname)
		indexname = nticard_prefix + indexname
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

	def _index_cards(self, cards, writer, language='en'):
		count = 0
		for _, data in cards.items():
			info, containerId = data
			if self.index_card_entry(writer, containerId, info, language):
				count += 1
		return count

	def process_book(self, idxspec, writer, language='en'):
		cards = {}
		toc = idxspec.book.toc
		def _loop(topic):
			m = self.process_topic(idxspec, topic, writer, language)
			cards.update(m)
			for t in topic.childTopics:
				_loop(t)
		_loop(toc.root_topic)

		result = self._index_cards(cards, writer, language)
		return result

_DefaultWhooshNTICardIndexer = _WhooshNTICardIndexer
