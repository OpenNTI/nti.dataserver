from __future__ import print_function, unicode_literals

from nti.contentrendering.RenderedBook import RenderedBook

class EmptyMockDocument(object):

    childNodes = ()

    def __init__(self):
        self.context = {}
        self.userdata = {}

    def getElementsByTagName(self, name): 
        return ()
    
def _phantom_function( htmlFile, scriptName, args, key ):
    return (key, {'ntiid': key[0]})

class NoPhantomRenderedBook(RenderedBook):

    def _get_phantom_function(self):
        return _phantom_function

