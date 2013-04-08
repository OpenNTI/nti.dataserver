#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from plasTeX import Command
from plasTeX import Environment
from plasTeX import DimenCommand
from plasTeX.Logging import getLogger


# SAJ: The logic of the glossary entry is derived from that of the footnote.
class ntiglossaryentry(Command):
    args = 'entryname self'
    mark = None

    def invoke(self, tex):
        # Add the glossary entry to the document
        output = Command.invoke(self, tex)
        userdata = self.ownerDocument.userdata
        if 'glossary' not in userdata:
            userdata['glossary'] = []
        userdata['glossary'].append(self)
        self.mark = self
        return output

