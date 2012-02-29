#!/usr/bin/env python
"""
Implementations of content fragment transformers.
"""
from __future__ import print_function, unicode_literals

import re

from zope import interface
from zope import component

from nti.contentrendering import interfaces

# Map from unicode to tex name
_TEX_OPERATORS = [('\u00d7', '\\times'),
				  ('\u2013', '-'),
				  ('\u2212', '-'),
				  ('\u2260', '\\neq'),
				  ('\u00f7', '\\div'),
				  ('\u2026', '\\ldots'),
				  ('\u221a', '\\surd'), # radicand
				  ('\u2192', '\\rightarrow'),
				  ('\uf0d0', '\\angle'),
				  ('\uf044', '\\triangle'),
				  ('\u2248', '\\approx')]
_TEX_OPERATOR_MAP = { ord(_k): _v for _k,_v in _TEX_OPERATORS }

def _escape_tex(text):
	escapes = [('$', '\\$'),
			   ('%', '\\%\\'),
			   ('\u00d7', '$\\times$'),
			   ('\u2013', '-'),
			   ('\u2212', '-'),
			   ('\u201c', '``'),
			   ('\u201d', "''"),
			   ('\u2019', "'"),
			   ('\u2014', '---'),
			   ('\u2260', '$\\neq$'),
			   ('\u00f7', '$\\div$'),
			   ('\u03c0', '$\\pi$'),
			   ('\u2026', '$\\ldots$'),
			   ('\u221a', '$\\surd$'), # radicand
			   ('\u2192', '$\\rightarrow$'),
			   ('\uf0d0', '$\\angle$'),
			   ('\uf044', '$\\triangle$'),
			   ('\u2248', '$\\approx$'),
			   ]
	escaped_text = text
	for escape in escapes:
		escaped_text = escaped_text.replace( escape[0], escape[1] )
	return escaped_text

_PLAIN_BINARY_OPS = ( '+', '-', '*', '/', '=', '<', '>', '\u2260' )
_UNICODE_OPS = [_x[0] for _x in _TEX_OPERATORS]

_PLAIN_ACCEPTS = ( '(', ')' )

_naturalNumberPattern = re.compile('^[0-9]+[.?,]?$') # Optional trailing punctuation
_realNumberPattern = re.compile('^[0-9]*\\.[0-9]*[.?,]?$') # Optional trailing punctuation
_SIMPLE_ALGEBRA_TERM_PAT = re.compile( r"^[0-9]+\.?[0-9]*[b-zB-Z" + '\u03C0]$' )
_PRE_SIMPLE_ALGEBRA_TERM_PAT = re.compile( r"^[a-zA-Z][0-9]+\.?[0-9]*$" )
_SIMPLE_ALGEBRA_VAR = re.compile( '^[a-zA-Z]$' )

_TRAILING_PUNCT = (',','.','?')

def is_equation_component( token ):
	if not token:
		return token # False for empty tokens
	return (token in _PLAIN_BINARY_OPS
			# Match '('
			or token in _PLAIN_ACCEPTS
			# Match '(7'
			or (token.startswith( '(' ) and is_equation_component( token[1:] ))
			# Match '7)'
			or (token.endswith( ')' ) and is_equation_component( token[0:-1] ))
			or (token[-1] in _TRAILING_PUNCT and is_equation_component( token[0:-1] ))
			or token in _UNICODE_OPS
			or _naturalNumberPattern.match( token )
			or _realNumberPattern.match( token )
			or _SIMPLE_ALGEBRA_TERM_PAT.match(token)
			or _PRE_SIMPLE_ALGEBRA_TERM_PAT.match( token )
			or _SIMPLE_ALGEBRA_VAR.match( token ))

def cleanup_equation_tokens( tokens ):
	"""
	Perform cleanups on the individual tokens that make up an
	equation before converting it to string form.

	:return: A 3-tuple: (before string, tokens, after_string)
	"""
	# This is a partial implementation that grows as needed
	if tokens[-1][-1] in _TRAILING_PUNCT:
		punct = tokens[-1][-1]
		tokens = list(tokens)
		tokens[-1] = tokens[-1][0:-1]
		return ('', tokens, punct )

	return ('',tokens,'')


@interface.implementer(interfaces.ILatexContentFragment)
@component.adapter(interfaces.IPlainTextContentFragment)
def PlainTextToLatexFragmentConverter(plain_text):
	# We do a crappy job of trying to parse out expression-like things
	# with a hand-rolled parser. There are certainly better ways. One might
	# be to extract the math parsing algorithm from plasTeX; we'd still have to
	# figure out what makes sense, though

	# First, tokenize on whitespace. If the math is poorly delimited, this
	# will fail
	tokens = plain_text.split()

	# Run through until we find an operator. Back up while the previous
	# tokens are numbers. Go forward while the tokens are numbers or operators.
	# repeat until we have consumed all the tokens
	accum = []
	# Each time through the loop we'll either consume an equation and everything
	# before it, or we'll take no action. When we reach the end naturally,
	# everything left is not an equation
	i = 0
#	import pdb; pdb.set_trace()
	while i < len(tokens):
		if tokens[i] in _PLAIN_BINARY_OPS:
			pointer = i - 1
			while pointer >= 0:
				if is_equation_component( tokens[pointer] ):
					pointer -= 1
				else:
					break
			if pointer == i - 1:
				# We didn't move backwards at all. This is not part of an equation
				i += 1
				continue
			beginning = pointer + 1 # We moved the cursor before the beginning
			pointer = i + 1
			while pointer < len(tokens):
				token = tokens[pointer]
				if is_equation_component( token ):
					pointer += 1
					if token[-1] in _TRAILING_PUNCT:
						break
				else:
					break
			if pointer == i + 1:
				# We didn't move forwards at all. Hmm. A dangling
				# part of an equation.
				i += 1
				continue
			end = pointer
			eq_tokens = tokens[beginning:end]
			bef, eq_tokens, aft = cleanup_equation_tokens( eq_tokens )
			eq = ' '.join(eq_tokens)
			eq = eq.translate( _TEX_OPERATOR_MAP )
			eq = bef + '$' + eq + '$' + aft

			# Everything before us goes in the accumulator
			accum.extend( [_escape_tex(x) for x in tokens[0:beginning]] )
			# and then us
			accum.append( eq )
			# and now we can remove the beginning and start over
			del tokens[0:end]
			i = 0
		else:
			# Not a constituent, go forward
			i += 1

	# Any tokens left go in the accumulator
	accum.extend( [_escape_tex(x) for x in tokens] )

	#

	return interfaces.LatexContentFragment( ' '.join( accum ) )
