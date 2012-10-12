from __future__ import print_function, unicode_literals

from zope import interface
from zope.component.interfaces import IFactory

from zopyx.txng3.core.interfaces import ISplitter

from nti.contentsearch import split_content

@interface.implementer(ISplitter)
class Splitter(object):

	def split(self, content):
		return split_content(content)

@interface.implementer(IFactory)
class SplitterFactory:

	def __call__(self, *args, **kwargs):
		splitter = Splitter()
		return splitter

	def getInterfaces(self):
		return interface.implementedBy(Splitter)

SplitterFactory = SplitterFactory()

