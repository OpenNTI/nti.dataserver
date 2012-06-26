from xml.dom.minidom import parseString


OMS = 'OMS'
OMA = 'OMA'
OMV = 'OMV'
OMI = 'OMI'
OMOBJ = 'OMOBJ'
OMF = 'OMF'


def binaryOperator(op, arg1, arg2):
	return '%s %s %s' % (arg1, op, arg2)

def unaryOperator(op, arg1):
	return '%s%s' % (op, arg1)

def latexMacro(macro, *args):
	result = '%s' % macro

	for arg in args:
		result += '{%s}' % arg

	return result

def sqrt(arg1, arg2):
	result = '\\sqrt'
	if arg2 != '2':
		result += '[%s]'% arg2
	result += '{%s}' % arg1
	return result

def power(num, pow):
	return '%s^{%s}' % (num, pow)

arith1 = { \
'plus' : [binaryOperator, '+', '#1', '#2'],	\
'unary_minus': [unaryOperator, '-', '#1'], \
'times' : [binaryOperator, '*', '#1', '#2'],	\
'power': [power,'#1', '#2'], \
'divide': [latexMacro, '\\frac', '#1', '#2'],\
'root' : [sqrt, '#1','#2' ],\
'minus' : [binaryOperator, '-', '#1', '#2'] \
}\

nums1 = {'pi' : '\\pi'}

class OpenMath2Latex(object):
	contentDicts = {}

	def __init__(self):
		self.contentDicts['arith1'] = arith1
		self.contentDicts['nums1'] = nums1
	def translate(self, openMathXML):
		dom = parseString(openMathXML)

		omobj = dom.firstChild

		if omobj.localName != OMOBJ:
			print 'Expected %s but found %s.  Are you sure this is open math' % (OMOBJ, omobj.localName)
			return '\\Unknown{%s}' % (omobj)


		oma = self.getChild(omobj, OMA)
		handler = self.handleOMA
		if oma == None or oma.localName != OMA:
			if hasattr( self, 'handle' + omobj.childNodes[0].localName ):
				handler = getattr( self, 'handle' + omobj.childNodes[0].localName )
				oma = omobj.childNodes[0]
			else:
				print 'Expected %s but found %s' % (OMA, getattr( oma, 'localName' ))
				return '\\Unknown{%s}' % (oma)

		return '$%s$' % handler(oma)

	def getChild(self, node, childName):
		for child in node.childNodes:
			if child.localName == childName:
				return child
		return None

	def handleOMS(self, node):
		'''
		Returns a tuple of the contentdictionary
		add operator name.

		<OMS cd="arith1" name="unary_minus"/>
		returns
		(arith1, unary_minus)

		e.g.
		'''

		cd = node.getAttribute('cd')
		name = node.getAttribute('name')

		return (cd, name)

	def handleOMA(self, node):
		#First child should be the operator
		children = node.childNodes

		translator = None
		args = None
		possibleArgs = []

		for child in children:


			if child.localName == OMS:

				cdname, opname = self.handleOMS(child)

				cd = self.contentDicts[cdname]

				content = None

				if cd:
					content = cd[opname]

				if content == None:
					print 'Unknown content for %s:%s' % (cdname, opname)
					return '\\Unknowncontent{%s}{%s}' % (cdname, opname)


				if isinstance(content, basestring):
					possibleArgs.append(content)
					continue

				translator = content[0]
				args = content[1:]

			elif child.localName == OMI:
				possibleArgs.append(self.handleOMI(child))

			elif child.localName == OMV:
				possibleArgs.append(self.handleOMV(child))

			elif child.localName == OMA:
				possibleArgs.append(self.handleOMA(child))

			elif child.localName == OMF:
				possibleArgs.append(self.handleOMF(child))

			else:
				continue

		if not translator:
			print 'No operator found'
			return '\\NoOperatorFound{%s}' % (node)

		translatorArgs = []

		if args:
			for arg in args:
				if arg[0] == '#':
					translatorArgs.append(possibleArgs.pop(0))
				else:
					translatorArgs.append(arg)

		return self.executeTranslator(translator, translatorArgs)

	def executeTranslator(self, func, args):
		return func(*args)

	def handleOMF(self, node):
		'''
		OMF has a dec attribute that contains
		the value.  e.g. <OMF decimal="40000"/>
		'''
		return node.getAttribute('dec')

	def handleOMV(self, node):
		'''
		OMV has a name attribute that contains
		the variable name.  e.g. <OMV name="a"/>
		'''
		return node.getAttribute('name')

	def handleOMI(self, node):
		'''
		OMI should have on child that is a text node
		e.g. <OMI>4</OMI>
		'''
		return node.firstChild.data
