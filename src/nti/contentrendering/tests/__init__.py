import nti.contentrendering


import zope.component

from nti.tests import ConfiguringTestBase as _ConfiguringTestBase

class ConfiguringTestBase(_ConfiguringTestBase):
	set_up_packages = (nti.contentrendering,)


class EmptyMockDocument(object):

	childNodes = ()

	def __init__(self):
		self.context = {}
		self.userdata = {}

	def getElementsByTagName(self, name): return ()

def _phantom_function( htmlFile, scriptName, args, key ):
	return (key, {'ntiid': key[0]})

from nti.contentrendering.RenderedBook import RenderedBook
class NoPhantomRenderedBook(RenderedBook):

	def _get_phantom_function(self):
		return _phantom_function
