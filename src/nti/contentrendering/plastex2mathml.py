from xml.dom import minidom
from StringIO import StringIO
import os, time, tempfile, shutil, re, string, pickle, codecs
import subprocess
from plasTeX.Imagers import WorkingFile, Image
import plasTeX
import xml.sax
from xml.sax.xmlreader import InputSource
import pdb

class plastex2mathml(object):

	compiler = 'ttm'

	def transform(self, document):
		### Convert math elements to mathml ###
		self.config=document.config
		# generate latex source

		# Start the document with a preamble
		self.source = StringIO()
		self.source.write('\\scrollmode\n')
		self.__writePreamble(document)
		self.source.write('\\begin{document}\n')



		mathNodes = document.getElementsByTagName('math')
		mathNodes.extend(document.getElementsByTagName('displaymath'))


		#Get elements by tag name seems to return some duplicates
		mathNodes = list(set(mathNodes))

		for math in mathNodes:
			print "Writing math node %s - %s" % (math, math.source)
			self.__writeNode(math)

		#Finish the document
		self.source.write('\n\\end{document}\\endinput')

		output = self.__compileLatex(self.source)

		#Load up the results into a dom
		parser = xml.sax.make_parser()
		parser.setEntityResolver(MyEntityResolver())

		mathmlDom = minidom.parse(output, parser)

		mathmls = mathmlDom.getElementsByTagName('math')


		print 'Generated %d from %d nodes' % (len(mathNodes), len(mathmls))

		for origmath, mathml in zip(mathNodes, mathmls):
				mathml.setAttribute('source', origmath.source)
				newNode=self.__minidom2plastexdom(document, mathml)
				parent=origmath.parentNode
				try:
					print 'Replacing %s' % origmath
					parent.replaceChild(newNode, origmath)
				except plasTeX.DOM.NotFoundErr, e:
					#Occasionally a nodes parent has no children.  This happens when the
					#node exists within a TexFragment stored as an attribute

					found=False
					if parent.attributes:
						print 'lookin %s for %s' % (origmath, mathml)
						for attrval in parent.attributes.values():
							if origmath in attrval.childNodes:
								print 'Found replacement %s for %s' % (newNode, origmath)
								attrval.replaceChild(newNode, origmath)
								found=True
								break

					if not found:
						print "Unable to replace %s with %s" % (origmath.toXML(), mathml.toxml())
						pdb.set_trace()




	def __minidom2plastexdom (self, plastexDoc, minidomElement):


		pElement = plastexDoc.createElement(minidomElement.tagName)

		#Add attributes
		if minidomElement.attributes:
			for key in minidomElement.attributes.keys():
				pElement.setAttribute(key, minidomElement.getAttribute(key))

		if minidomElement.childNodes:
			for child in minidomElement.childNodes:
				if getattr(child, 'data', None):
					pElement.appendChild(child.data)
				else:
					pElement.appendChild(self.__minidom2plastexdom(plastexDoc, child))

		return pElement

	def __writeNode(self, node, context=''):
		"""
		Write LaTeX source for the image

		Arguments:
		filename -- the name of the file that will be generated
		code -- the LaTeX code of the image
		context -- the LaTeX code of the context of the image

		"""
		self.source.write('%s\n%s\n' % (context, node.source))



	def __writePreamble(self, document):
		""" Write any necessary code to the preamble of the document """
		self.source.write(document.preamble.source)
		self.source.write('\\makeatletter\\oddsidemargin -0.25in\\evensidemargin -0.25in\n')


	def __compileLatex(self, source):
		"""
		Compile the LaTeX source

		Arguments:
		source -- the LaTeX source to compile

		Returns:
		file object corresponding to the output from LaTeX

		"""
		cwd = os.getcwd()

		# Make a temporary directory to work in
		tempdir = tempfile.mkdtemp()
		os.chdir(tempdir)

		filename = 'math.tex'

		# Write LaTeX source file
		if self.config['images']['save-file']:
			self.source.seek(0)
			codecs.open(os.path.join(cwd,filename), 'w', self.config['files']['input-encoding']).write(self.source.read())
		self.source.seek(0)
		codecs.open(filename, 'w', self.config['files']['input-encoding']).write(self.source.read())

		# Run LaTeX
		os.environ['SHELL'] = '/bin/sh'
		program = self.compiler



		os.system(r"%s %s" % (program, filename))
		#JAM: This does not work. Fails to read input
		# cmd = str('%s %s' % (program, filename))
		# print shlex.split(cmd)
		# p = subprocess.Popen(shlex.split(cmd),
		# 			 stdout=subprocess.PIPE,
		# 			 stderr=subprocess.STDOUT,
		# 			 )
		# while True:
		# 	line = p.stdout.readline()
		# 	done = p.poll()
		# 	if line:
		# 		imagelog.info(str(line.strip()))
		# 	elif done is not None:
		# 		break

		output = None
		for ext in ['.xml']:
			if os.path.isfile('math'+ext):
				output = WorkingFile('math'+ext, 'rb', tempdir=tempdir)
				break

		# Change back to original working directory
		os.chdir(cwd)

		return output


class MyEntityResolver(xml.sax.handler.EntityResolver):
	def resolveEntity(self, p, s):
		return InputSource(s)
