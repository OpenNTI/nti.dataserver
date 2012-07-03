import xml.dom
import sys

class Range(object):

	detached = False
	ancestor = None
	start_node = None
	end_node = None
	start_offset = None
	end_offset = None
	collapsed = False;
	START_TO_START = 0
	START_TO_END = 1
	END_TO_START = 2
	END_TO_END = 3

	def is_ancestor(self,ancestor,descendant):
		if ancestor == descendant: 
			return True
		
		if ancestor == None or descendant == None:
			return False

		return self.is_ancestor(ancestor,descendant.parentNode)



	def find_common_ancestor(self,a,b):
		ancestor = a
		while ancestor is not None and self.is_ancestor(ancestor,b) == False:
			ancestor = ancestor.parentNode
		return ancestor

	def childIndex(self,node):
		children = node.parentNode.childNodes
		for i,c in enumerate(children):
			if c == node:
				return i

	def compare(self, a, a_offset,b,b_offset): 
		# Result of 1 equivalent to a > b, 0 equal, -1 b > a
		if a == b: 
			if a_offset < b_offset:
				return -1 
			if a_offset > b_offset:
				return 1
			return 0

		a_index, b_index = -1,-1
		ancestor = self.find_common_ancestor(a,b)
		if ancestor is None:
			return None

		children = ancestor.childNodes
		for i,c in enumerate(children):
			if self.is_ancestor(c,a):
				a_index = i
			if self.is_ancestor(c,b):
				b_index = i

		if self.is_ancestor(a,b):
			if b_index < a_offset:
				return 1
			return -1

		if self.is_ancestor(b,a):
			if a_index < b_offset:
				return -1
			return 1

		if b_index < a_index: 
			return 1

		return -1;

	def pointInside(self, node, offset):
		cl = self.compare(self.start_node,self.start_offset,node,offset)
		cr = self.compare(self.end_node,self.end_offset,node,offset)
		return cl <= 0 and cr >= 0

	def compareBoundaryPoints(self, how, other):
		if how == self.START_TO_START:
			c = self.compare(self.start_node,self.start_offset,
							other.start_node,other.start_offset)
		if how == self.START_TO_END:
			c = self.compare(self.start_node,self.start_offset,
							other.end_node,other.end_offset)
		if how == self.END_TO_START:
			c = self.compare(self.end_node,self.end_offset,
							other.start_node,other.start_offset)
		if how == self.END_TO_END:
			c = self.compare(self.end_node,self.end_offset,
							other.end_node,other.end_offset)
		return c

	def update(self):
		if self.start_node is not None and self.end_node is not None:
			self.ancestor = self.find_common_ancestor(self.start_node,self.end_node)
		if self.compare(self.end_node,self.end_offset,self.start_node,self.start_offset) in (0,-1):
			self.collapsed = True

	def set_start(self,node,offset):
		self.start_node = node
		self.start_offset = offset
		if self.start_node.nodeType == self.start_node.TEXT_NODE:
			if self.start_offset > len(self.start_node.data):
				self.start_offset = len(self.start_node.data)
		self.update()

	def set_end(self,node,offset):
		self.end_node = node
		self.end_offset = offset
		if self.end_node.nodeType == self.end_node.TEXT_NODE:
			if self.end_offset > len(self.end_node.data):
				self.end_offset = len(self.end_node.data)
		self.update()

	def set_start_before(self,node):
		self.start_node = node.parentNode
		self.start_offset = self.childIndex(node)
		self.update()

	def set_start_after(self,node):
		self.start_node = node.parentNode
		self.start_offset = self.childIndex(node) + 1
		self.update()

	def set_end_before(self,node):
		self.end_node = node.parentNode
		self.end_offset = self.childIndex(node)
		self.update()

	def set_end_after(self,node):
		self.end_node = node.parentNode
		self.end_offset = self.childIndex(node) + 1
		self.update()

	def collapse(self,to_start):
		if to_start:
			self.end_node = self.start_node
			self.end_offset = self.start_offset
		else:
			self.start_node = self.end_node
			self.end_offset = self.start_offset
		self.ancestor = self.start_node
		self.collapsed = True

	# Mainly for debugging purposes
	"""def path_from_root(self,node):
		cn = node
		result = []
		while cn.parentNode is not None:
			result = [self.childIndex(cn)] + result
			cn = cn.parentNode
		return result"""

	# Returns a string of all text between start and end in the order that it
	# would appear in the XML DOM representation
	def stringify(self):
		if self.collapsed:
			return ""
		if self.ancestor is None: raise Exception("No common ancestor found")
		cur_node,cur_offset = self.start_node, self.start_offset
		result = []
		while True:
			if cur_node.nodeType == cur_node.TEXT_NODE:
				if cur_node == self.end_node:
					result.append(cur_node.data[cur_offset:self.end_offset])
					break
				else:
					result.append(cur_node.data[cur_offset:])
					cur_node = cur_node.parentNode
					cur_offset = self.childIndex(cur_node) + 1
			else:
				if cur_node == self.end_node and cur_offset == self.end_offset:
					break
				if cur_offset < len(cur_node.childNodes):
					cur_node = cur_node.childNodes[cur_offset]
					cur_offset = 0
				else:
					cur_offset = self.childIndex(cur_node) + 1
					cur_node = cur_node.parentNode
		return ''.join(result)

	__str__ = stringify
