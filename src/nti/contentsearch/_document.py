# Copyright (c) 2008 Agendaless Consulting and Contributors.
# (http://www.agendaless.com), All Rights Reserved
# Disclaimer
#	THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND
#	ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
#	TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
#	PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#	HOLDERS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#	EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
#	TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#	DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#	ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
#	TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
#	THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
#	SUCH DAMAGE.

from __future__ import print_function, unicode_literals

from repoze.catalog.document import DocumentMap as rcDocumentMap

class DocumentMap(rcDocumentMap):

	def _reverse(self, x):
		idx = 3 if x < 0 else 2
		x = int(bin(x)[idx:].zfill(31)[::-1], 2)
		if idx == 2:
			return min(x, self.family.maxint)
		else:
			return max(x, self.family.minint)
	
	def new_docid(self):
		while True:
			if self._v_nextid is None:
				self._v_nextid = self._randrange(self.family.minint, self.family.maxint)
			uid = self._reverse(self._v_nextid)
			self._v_nextid += 1
			if uid not in self.docid_to_address:
				return uid
			self._v_nextid = None
			
