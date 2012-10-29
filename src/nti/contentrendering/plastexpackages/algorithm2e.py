#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import re

from zope import interface

from nti.contentrendering import plastexids
from nti.contentrendering.resources import interfaces as res_interfaces

from plasTeX import Base

# SAJ: This is a partial implementation of the algorithm package.  Full support is planned.

class _Ignored(Base.Command):
    unicode = ''
    def invoke( self, tex ):
        return []

class DontPrintSemicolon(_Ignored):
    pass

class SetNoLine(_Ignored):
    pass

class SetAlgoNoLine(_Ignored):
    pass

class KwData(Base.Command):
    blockType = True
    args = 'self'

class KwResult(Base.Command):
    blockType = True
    args = 'self'

class function(Base.Environment):
    args = '[placement]'
    blockType = True

    class TitleOfAlgo(Base.Command):
        blockType = True
        args = 'self'

    class semicolon(Base.Command):
        macroName = ';'


# Commands for different types of If / If-Then / If-Then-Else blocks

class If(Base.Command):
    blockType = True
    args = '(comment) self then'

class uIf(If):
    pass

class ElseIf(If):
    pass

class uElseIf(If):
    pass

class Else(Base.Command):
    blockType = True
    args = '(comment) self'

class uElse(Else):
    pass

class eIf(Base.Command):
    blockType = True
    args = '(then_comment) self then (else_comment) else'

# Commands for different types of pre-condition based looping blocks

class _PreLoop(Base.Command):
    blockType = True
    args = '(comment) self loop'

class For(_PreLoop):
    pass

class While(_PreLoop):
    pass

class ForEach(_PreLoop):
    pass

class ForAll(_PreLoop):
    pass
