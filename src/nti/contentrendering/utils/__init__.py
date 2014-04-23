# -*- coding: utf-8 -*-
"""
Content rendering utils module

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.contentrendering.RenderedBook import RenderedBook

class EmptyMockDocument(object):

    childNodes = ()

    def __init__(self):
        self.context = {}
        self.userdata = {}

    def getElementsByTagName(self, name):
        return ()

def _phantom_function(htmlFile, scriptName, args, key):
    return (key, {'ntiid': key[0]})

class NoPhantomRenderedBook(RenderedBook):

    def _get_phantom_function(self):
        return _phantom_function

class NoConcurrentPhantomRenderedBook(RenderedBook):

    # Replaces RenderedBook.runPhandomOnPages with a version that does not require
    # phantomJS and does not  call the sometimes problematic concurrency module.
    # Useful for the creation of RenderedBook objects where we are only going to alter
    # basic things such as the index or sharewith attribute.
    def runPhantomOnPages(self, script, *args):
        results = {}
        eclipseTOC = self.toc
        nodesForPages = eclipseTOC.getPageNodes()
        for node in nodesForPages:
            key = (node.getAttribute(b'ntiid'),
                   node.getAttribute(b'href'),
                   node.getAttribute(b'label'))
            result = {'ntiid': key[0]}
            results[key] = result
        return results
