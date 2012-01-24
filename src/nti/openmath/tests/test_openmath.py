import unittest, os

from nti.openmath import OpenMath2Latex


class TestAssessment(unittest.TestCase):

	inputDir = 'openmath'

	def setUp(self):
		self.translator = OpenMath2Latex()

	def test_simplemath(self):

		result = self.translateOpenMath('simplemath.xml')

		self.assertEqual('$31 + 3$', result)

		result = self.translateOpenMath('simplemath2.xml')

		self.assertEqual('$31 - 3$', result)

		result = self.translateOpenMath('simplemath3.xml')

		self.assertEqual('$31 * 3$', result)

		result = self.translateOpenMath('simplemath4.xml')

		self.assertEqual('$-31$', result)

	def test_mathwithvars(self):
		result = self.translateOpenMath('varmath.xml')

		self.assertEqual('$x + 3$', result)

		result = self.translateOpenMath('varmath2.xml')

		self.assertEqual('$x - 3$', result)

		result = self.translateOpenMath('varmath3.xml')

		self.assertEqual('$x * 3$', result)

		result = self.translateOpenMath('varmath4.xml')

		self.assertEqual('$-x$', result)

	def test_basicmacros(self):
		result = self.translateOpenMath('macromath.xml')

		self.assertEqual('$\\frac{1}{2}$', result)

		result = self.translateOpenMath('macromath2.xml')

		self.assertEqual('$\\frac{1}{x}$', result)

		result = self.translateOpenMath('macromath3.xml')

		self.assertEqual('$\\sqrt{x}$', result)

		result = self.translateOpenMath('macromath4.xml')

		self.assertEqual('$\\sqrt[3]{64}$', result)

	def test_symbol(self):
		result = self.translateOpenMath('symbol.xml')

		self.assertEqual('$\\frac{25 * \\pi}{2}$', result)

	def test_complex(self):
		result = self.translateOpenMath('complexmath.xml')

		self.assertEqual('$\\sqrt[3]{31} + \\frac{q^{2} - 1}{q - 1}$', result)

	def test_float(self):
		result = self.translateOpenMath('floatmath.xml')

		self.assertEqual('$40000.00 + 3$', result)

	def translateOpenMath(self, file_name):
		xml = open(os.path.join( os.path.dirname(__file__), 'openmath', file_name))
		result = self.translator.translate(xml.read())
		xml.close()

		return result

if __name__ == '__main__':
	unittest.main()
