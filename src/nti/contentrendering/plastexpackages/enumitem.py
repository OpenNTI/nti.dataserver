#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from plasTeX import Base, Command, Environment

# SAJ: Extremely limited support for the enumitem package.

class enumerate_( Base.enumerate_ ):
    macroName = 'enumerate'
    args = '[ options ]'

    def invoke( self, tex ):
        _t = super( enumerate_, self ).invoke(tex)

        # Only attempt to parse options if we are initialing the environment, and not when we are exiting it.
        if self.macroMode != Environment.MODE_END:
            if 'options' in self.attributes:
                options = self.attributes['options'].textContent.split(',')
            else:
                options = []
            if options and options[0] in [ '1', 'a', 'A', 'i', 'I' ]:
                self.attributes['type'] = options[0]
                options = options[1:]

            self.options = {}
            # Set start to the default value of 1. If there is a specified value in the doc it will override this.
            self.options['start'] = 1
            if options:
                for option in options:
                    o = option.strip().split('=')
                    self.options[o[0]] = o[1]

            # Fast forward the counter to the start 
            counter = Base.List.counters[Base.List.depth-1]
            self.ownerDocument.context.counters[counter].value = int(self.options['start']) - 1

        return _t
