from __future__ import print_function, unicode_literals

import re
import six
import html5lib
from lxml import etree
from html5lib import treebuilders

from nti.contentfragments.interfaces import IHTMLContentFragment

import logging
logger = logging.getLogger(__name__)

class GrubberHyperlinkifier(object):
	
	# http://daringfireball.net/2010/07/improved_regex_for_matching_urls
	
	grubber_v1 = (u'((?:[a-z][\\w-]+:(?:/{1,3}|[a-z0-9%])|www\\d{0,3}[.]|[a-z0-9.\\-]+',
				  u'[.][a-z]{2,4}/)(?:[^\\s()<>]+|\\(([^\\s()<>]+|(\\([^\\s()<>]+\\)))*\\))+',
				  u'(?:\\(([^\\s()<>]+|(\\([^\\s()<>]+\\)))*\\)|[^\\s`!()\\[\\]{};:\'".,<>?',
				  u'\xab\xbb\u201c\u201d\u2018\u2019]))')

	grubber_v2 = (u'((?:https?://|www\\d{0,3}[.]|[a-z0-9.\\-]+[.][a-z]{2,4}/)(?:[^\\s()<>]+',
				  u'|\\(([^\\s()<>]+|(\\([^\\s()<>]+\\)))*\\))+(?:\\(([^\\s()<>]+|(\\([^\\s()<>]+',
				  u'\\)))*\\)|[^\\s`!()\\[\\]{};:\'".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))')

	grubber_v1_pattern = re.compile(''.join(grubber_v1))
	grubber_v2_pattern = re.compile(''.join(grubber_v2))

	def _a_builder(self, node, pattern, is_text=True):
		field = 'text' if is_text else 'tail'
		text = getattr(node, field, None)
		if text:
			result = []
			m = pattern.search(text)
			while m:
				end = m.end()
				start = m.start()
				result.append(text[0:start])
				e = etree.Element('a', href=text[start:end])
				e.text = text[start:end]
				result.append(e)
				text = text[end:]
				m = pattern.search(text)
				
			if text:	
				result.append(text)
				
			setattr(node, field, None)
			for i, e in enumerate(result):
				if isinstance(e, six.string_types):
					if i == 0:
						setattr(node, field, e)
					else:
						result[i-1].tail = e
				elif is_text: 
					node.append(e)
				else:
					parent = node.getparent()
					if parent is not None:
						parent.append(e)

				
	def _link_finder(self, node):
		self._a_builder(node, self.grubber_v1_pattern, True)
		self._a_builder(node, self.grubber_v1_pattern, False)
	
	def convert(self, html_fragment):
		if IHTMLContentFragment.providedBy(html_fragment):
			p = html5lib.HTMLParser( tree=treebuilders.getTreeBuilder("lxml"), namespaceHTMLElements=False )
			doc = p.parse( html_fragment )
			for node in doc.iter():
				self._link_finder(node)
				
			docstr = unicode(etree.tostring(doc))
			html_fragment = html_fragment.__class__(docstr)
		return html_fragment
	
	def __call__(self, html_fragment):
		return self.convert(html_fragment)

	