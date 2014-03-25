#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Partial implementation of the algorithm package.

Full support is planned.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Base

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

class SetKw(Base.Command):
    blockType = True
    args = 'name self'

class SetKwRepeat(Base.Command):
    blockType = True
    args = 'name self until'

class function(Base.Environment):
    args = '[placement]'
    blockType = True

    class TitleOfAlgo(Base.Command):
        blockType = True
        args = 'self'

    class semicolon(Base.Command):
        macroName = ';'

class procedure(Base.Environment):
    args = '[placement]'
    blockType = True

    class TitleOfAlgo(Base.Command):
        blockType = True
        args = 'self'

    class semicolon(Base.Command):
        macroName = ';'


class Begin(Base.Command):
    blockType = True
    args = '(comment) self'

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

# Commands for different types of post-condition based looping blocks

class _PostLoop(Base.Command):
    blockType = True
    args = '(comment) self loop (comment2)'

class Repeat(_PostLoop):
    pass
