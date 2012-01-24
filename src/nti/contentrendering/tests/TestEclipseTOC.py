import unittest
import os
from nti.contentrendering.RenderedBook import EclipseTOC



class TestEclipseTOC(unittest.TestCase):

	def setUp(self):
		self.eclipsetoc = EclipseTOC( os.path.join( os.path.dirname(__file__),  'eclipse-toc.xml') )

	def test_getrootnode(self):
		rootNode = self.eclipsetoc.getRootTOCNode()

		self.assertIsNotNone(rootNode, 'root node should not be none')

		self.assertValidNode(rootNode, ntiid='aops-prealgebra-31', href='index.html',
							 label='Prealgebra', height='11990', icon='icons/chapters/PreAlgebra-cov-icon.png')



	def test_getnodebyid(self):

		rootNode = self.eclipsetoc.getRootTOCNode()

		self.assertEqual(rootNode, self.eclipsetoc.getPageNodeWithNTIID('aops-prealgebra-31'))

		self.assertAttribute(self.eclipsetoc.getPageNodeWithNTIID('aops-prealgebra-25') ,'ntiid', 'aops-prealgebra-25')


	def test_getnodebyattribute(self):
		rootNode = self.eclipsetoc.getRootTOCNode()

		self.assertEqual(rootNode, self.eclipsetoc.getPageNodeWithAttribute('label', value='Prealgebra')[0])

		self.assertAttribute(self.eclipsetoc.getPageNodeWithAttribute('label', 'Greatest Common Divisor')[0], 'label', 'Greatest Common Divisor')


	def test_getPageNodes(self):
		nodes = self.eclipsetoc.getPageNodes()

		self.assertEqual(31, len(nodes))

		labels = [node.getAttribute('label') for node in nodes]

		self.assertFalse('Index' in labels)

	def assertValidNode(self, node, ntiid=None, href=None, label=None,
						height=None, icon=None):

		self.assertIsNotNone(node, 'node should not be none')

		if ntiid:
			self.assertAttribute(node, 'ntiid', ntiid)

		if href:
			self.assertAttribute(node, 'href', href)

		if label:
			self.assertAttribute(node, 'label', label)

		if height:
			self.assertAttribute(node, 'NTIRelativeScrollHeight', height)

		if icon:
			self.assertAttribute(node, 'icon', icon)

	def assertAttribute(self, node, attrname, attrval):
		self.assertIsNotNone(node, 'node should not be none')

		self.assertTrue(hasattr(node, 'hasAttribute'), '%s isn\'t a node with attributes' % node)

		self.assertTrue(node.hasAttribute(attrname), '%s has no attribute named %s' % (node, attrname))

		value = node.getAttribute(attrname)

		self.assertEqual(value, attrval, 'For node %s, attribute %s expected value %s but got %s' % (node, attrname, attrval, value))



if __name__ == '__main__':
	unittest.main()
