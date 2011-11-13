import unittest

from nti.assessment import *


class TestAssessment(unittest.TestCase):

	def test_mathTexToDOM(self):
		mathStrings = ['$1$','$1+2$','$\\frac{1}{2}$']

		maths = mathTexToDOMNodes(mathStrings)

		self.assertEqual(len(mathStrings), len(maths),'Expected %d nodes but got %d' % (len(mathStrings), len(maths)))

		for math in maths:
			self.assertIsInstance(math, plasTeX.Base.Math.math, 'Expected all nodes to be math nodes but got %s'%math)

	def test_mathequalsistransitive(self):
		math1, math2, math3 = mathTexToDOMNodes(['$10 $','$10$',' $ 10$'])

		self.assertMathNodesEqual(math1, math2)
		self.assertMathNodesEqual(math2, math3)

		self.assertMathNodesEqual(math1, math3, '%s == %s and %s == %s but %s != %s!'\
						 %(math1.source, math2.source, math2.source, math3.source, math1.source, math3.source))

	def test_naturalnumbers(self):
		#Test things that should be equal are
		math1, math2, math3, math4 = mathTexToDOMNodes(['$7$','$ 7$',' $ 7$','$ 7 $'])

		self.assertMathNodesEqual(math1, math2)
		self.assertMathNodesEqual(math1, math3)
		self.assertMathNodesEqual(math1, math4)

		#Test things that should NOT be equal are not
		math1, math2, math3, math4 = mathTexToDOMNodes(['$7$','$7.0$','$9$', '$70$'])

		self.assertMathNodesNotEqual(math1, math2)
		self.assertMathNodesNotEqual(math1, math3)
		self.assertMathNodesNotEqual(math1, math4)

	def test_simplemacros_nokids(self):
		#Test things that should be equal are
		math1, math2, math3, math4 = mathTexToDOMNodes(['$\\frac{1}{2}$','$\\frac{1 }{ 2 }$',' $\\frac{ 1 }{2}$','$ \\frac {1} {2}$'])

		self.assertMathNodesEqual(math1, math2)
		self.assertMathNodesEqual(math1, math3)
		self.assertMathNodesEqual(math1, math4)

		math1, math2, math3, math4 = mathTexToDOMNodes(['$\\sqrt{2}$','$\\sqrt{ 2 }$','$\\sqrt[3]{2}$','$ \\sqrt[3]{2}$'])

		self.assertMathNodesEqual(math1, math2)
		self.assertMathNodesEqual(math3, math4)


		math1, math2, math3, math4 = mathTexToDOMNodes(['$\\frac{1}{2}$','$\\frac{2}{4}$','$1/2 $','$ \\frac{4}{8}$'])

		self.assertMathNodesNotEqual(math1, math2)
		self.assertMathNodesNotEqual(math1, math3)
		self.assertMathNodesNotEqual(math1, math4)

		math1, math2, math3, math4 = mathTexToDOMNodes(['$\\sqrt{2}$','$\\sqrt{ 4 }$','$\\sqrt[3]{2}$','$ \\sqrt[43]{2}$'])

		self.assertMathNodesNotEqual(math1, math2)
		self.assertMathNodesNotEqual(math3, math4)

	@unittest.skip('Requires parse tree implementation')
	def test_exprinfractions(self):
		math1, math2 = mathTexToDOMNodes(['$\\frac{1+x}{2}$','$\\frac{1 + x}{2}$'])
		self.assertMathNodesEqual(math1,math2)

	@unittest.skip('Requires parse tree implementation')
	def test_expr(self):
		math1, math2, math3, math4 = mathTexToDOMNodes(['$1 + x$','$1+x$','$x+1$','$x + 1$'])
		self.assertMathNodesEqual(math1,math2)
		self.assertMathNodesEqual(math1,math3)
		self.assertMathNodesEqual(math1,math4)

	def test_symbols(self):
		math1, math2, math3, math4 = mathTexToDOMNodes(['$25\\pi$','$ 25 \\pi$','$25 \\pi $','$ 25\\pi $'])
		self.assertMathNodesEqual(math1, math2)
		self.assertMathNodesEqual(math1, math3)
		self.assertMathNodesEqual(math1, math4)

		math1, math2 = mathTexToDOMNodes(['$25\\pi$','$42\\pi$'])
		self.assertMathNodesNotEqual(math1, math2)

	def test_tuples(self):

		math1, math2, math3, math4 = mathTexToDOMNodes(['$(-1, 2)$','$(-1,2)$','$( -1, 2 )$','$(-1,2)$'])
		self.assertMathNodesEqual(math1, math2)
		self.assertMathNodesEqual(math1, math3)
		self.assertMathNodesEqual(math1, math4)

		math1, math2 = mathTexToDOMNodes(['$(1, 2)$','$(-1, -2)$'])
		self.assertMathNodesNotEqual(math1, math2)

	def test_time(self):
		#Test things that should be equal are
		math1, math2, math3, math4, math5 = mathTexToDOMNodes(['$3:30$', '$ 3:30$','$3:30 $','$ 3:30 $','$3 : 30$'])

		self.assertMathNodesEqual(math1, math2)
		self.assertMathNodesEqual(math1, math3)
		self.assertMathNodesEqual(math1, math4)
		self.assertMathNodesEqual(math1, math5)

		#Things that should not be equal
		math1, math2, math3, math4, math5 = mathTexToDOMNodes(['$3:30$', '$3:31$','$3:31 $','$ 5:30 $','$330$'])

		self.assertMathNodesNotEqual(math1, math2)
		self.assertMathNodesNotEqual(math1, math3)
		self.assertMathNodesNotEqual(math1, math4)
		self.assertMathNodesNotEqual(math1, math5)

	def test_simplemacros_kids(self):
		#Test things that should be equal are
		math1, math2, math3, math4 = mathTexToDOMNodes(['$3.2x10^32$','$3.2 x 10^32$','$1.4x10^\\frac{1}{2}$','$ 1.4 x  10^\\frac{ 1}{2}$'])

		self.assertMathNodesEqual(math1, math2)
		self.assertMathNodesEqual(math3, math4)

		#Things that should not be equal
		math1, math2, math3, math4 = mathTexToDOMNodes(['$3.2x10^32$','$3.2 x 10^33$','$1.14x10^32$','$ 1.4 x  10^32$'])

		self.assertMathNodesNotEqual(math1, math2)
		self.assertMathNodesNotEqual(math3, math4)


	def assertMathNodesEqual(self, math1, math2, message=None):
		if not message:
			message = '%s != %s!' % (math1.source, math2.source)

		self.assertTrue(mathIsEqual(math1, math2), message)

	def assertMathNodesNotEqual(self, math1, math2, message=None):
		if not message:
			message = '%s != %s!' % (math1.source, math2.source)

		self.assertFalse(mathIsEqual(math1, math2), message)

	def test_assess(self):
		quiz = {1 : MockQuiz(['$5.00$','$5$']),\
				2 : MockQuiz(['$12$']),\
				3 : MockQuiz(['$15.37$']),\
				4 : MockQuiz(['$1+x$']),\
				5 : MockQuiz(['$\\frac{2}{3}$']),\
				6 : MockQuiz(['$10$']),\
				7 : MockQuiz(['$42$']),\
				8 : MockQuiz(['$210$']),\
				9 : MockQuiz(['$6$']),\
				10 : MockQuiz(['$0$'])}

		responses = {1: '5', 2: '12', 3: '15.37', 4: '1 + x', 5:'\\frac{2}{3}', 6: '10', \
					 7 : '42', 8: '210', 9: '6', 10: '0'}


		expectedResults = {1: True, 2: True, 3: True, 4:True, 5: True, 6:True, \
							 7:True, 8:True, 9:True, 10:True}
		results = assess(quiz, responses)
		self.assertEqual(expectedResults, results)




		responses[3] = '15'
		responses[10] = '$1$'

		expectedResults[3] = False
		expectedResults[10] = False
		results = assess(quiz, responses)
		self.assertEqual(expectedResults, results)


		responses[4] = '<OMOBJ xmlns="http://www.openmath.org/OpenMath" '+ \
					   'version="2.0" cdbase="http://www.openmath.org/cd"> '+\
					   '<OMA><OMS cd="arith1" name="plus"/><OMI>1</OMI><OMV name="x"/></OMA></OMOBJ>'
		expectedResults[4] = True

		responses[5] = '<OMOBJ xmlns="http://www.openmath.org/OpenMath" '+\
					   'version="2.0" cdbase="http://www.openmath.org/cd"> '+\
					   '<OMA><OMS cd="arith1" name="divide"/><OMI>1</OMI> '+\
					   '<OMS cd="nums1" name="pi"/></OMA></OMOBJ>'

		expectedResults[5] = False
		results = assess(quiz, responses)
		self.assertEqual(expectedResults, results)


class MockQuiz(object):
	def __init__(self, answers):
		if not answers:
			answers = ['No answer']
		self.answers = answers

if __name__ == '__main__':
	unittest.main()
