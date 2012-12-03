from __future__ import print_function, unicode_literals

from zope import interface

from nti.contentprocessing.stemmers import interfaces as stemmer_interfaces

@interface.implementer(stemmer_interfaces.IStemmer)
class LovinsStemmer(object):
	""" Implementation of Lovins Stemmer - from kea.stemmers """
	
	# C version compatibility mode (emulates bugs in original C implementation)
	m_CompMode = True

	m_l11 = {"alistically":"B", "arizability":"A", "izationally": "B"}
	
	m_l10 = {"antialness": "A", "arisations": "A", "arizations":"A", "entialness": "A"}
	
	m_l9 = {"allically":" C", "antaneous": "A", "antiality": "A", "arisation": "A", "arization": "A",
			"ationally": "B", "ativeness": "A", "eableness": "E", "entations": "A", "entiality": "A",
			"entialize": "A", "entiation": "A", "ionalness": "A", "istically": "A", "itousness": "A", 
			"izability": "A", "izational": "A"}
	
	m_l8 = {"ableness": "A", "arizable": "A", "entation": "A", "entially": "A", "eousness": "A",
			"ibleness": "A", "icalness": "A", "ionalism": "A", "ionality": "A", "ionalize": "A",
			"iousness": "A", "izations": "A", "lessness": "A"}

	m_l7 = {"ability": "A", "aically": "A", "alistic": "B", "alities": "A", "alities": "A", "ariness": "E",
			"aristic": "A", "arizing": "A", "ateness": "A", "atingly": "A", "ational": "B", "atively": "A",
			"ativism": "A", "elihood": "E", "encible": "A", "entally": "A", "entials": "A", "entiate": "A",
			"entness": "A", "fulness": "A", "ibility": "A", "icalism": "A", "icalist": "A", "icality": "A",
			"icalize": "A", "ication": "G", "icianry": "A", "ination": "A", "ingness": "A", "ionally": "A",
			"isation": "A", "ishness": "A", "istical": "A", "iteness": "A", "iveness": "A", "ivistic": "A",
			"ivities": "A", "ization": "F", "izement": "A", "oidally": "A", "ousness": "A"}

	m_l6 = {"aceous": "A", "acious": "B", "action": "G", "alness": "A", "ancial": "A", "ancies": "A", 
			"ancing": "B", "ariser": "A", "arized": "A", "arizer": "A", "atable": "A", "ations": "B", 
			"atives": "A", "eature": "Z", "efully": "A", "encies": "A", "encing": "A", "ential": "A", 
			"enting": "C", "entist": "A", "eously": "A", "ialist": "A", "iality": "A", "ialize": "A", 
			"ically": "A", "icance": "A", "icians": "A", "icists": "A", "ifully": "A", "ionals": "A", 
			"ionate": "D", "ioning": "A", "ionist": "A", "iously": "A", "istics": "A", "izable": "E", 
			"lessly": "A", "nesses": "A", "oidism": "A" }

	m_l5 = {"acies": "A", "acity": "A", "aging": "B", "aical": "A", "alism": "B", "ality": "A", 
			"alize": "A", "allic": "b", "anced": "B", "ances": "B", "antic": "C", "arial": "A", 
			"aries": "A", "arily": "A", "arity": "B", "arize": "A", "aroid": "A", "ately": "A", 
			"ating": "I", "ation": "B", "ative": "A", "ators": "A", "atory": "A", "ature": "E", 
			"early": "Y", "ehood": "A", "eless": "A", "ement": "A", "enced": "A", "ences": "A", 
			"eness": "E", "ening": "E", "ental": "A", "ented": "C", "ently": "A", "fully": "A", 
			"ially": "A", "icant": "A", "ician": "A", "icide": "A", "icism": "A", "icist": "A", 
			"icity": "A", "idine": "I", "iedly": "A", "ihood": "A", "inate": "A", "iness": "A", 
			"ingly": "B", "inism": "J", "inity": "c", "ional": "A", "ioned": "A", "ished": "A", 
			"istic": "A", "ities": "A", "itous": "A", "ively": "A", "ivity": "A", "izers": "F", 
			"izing": "F", "oidal": "A", "oides": "A", "otide": "A", "ously": "A" }
	
	m_l5.update({"elity": "A"} if m_CompMode else {"alist": "A",  "elily": "A"})
	
	m_l4 = {"able": "A", "ably": "A", "ages": "B", "ally": "B", "ance": "B", "ancy": "B", "ants": "B", 
			"aric": "A", "arly": "K", "ated": "I", "ates": "A", "atic": "B", "ator": "A", "ealy": "Y", 
			"edly": "E", "eful": "A", "eity": "A", "ence": "A", "ency": "A", "ened": "E", "enly": "E", 
			"eous": "A", "hood": "A", "ials": "A", "ians": "A", "ible": "A", "ibly": "A", "ical": "A", 
			"ides": "L", "iers": "A", "iful": "A", "ines": "M", "ings": "N", "ions": "B", "ious": "A", 
			"isms": "B", "ists": "A", "itic": "H", "ized": "F", "izer": "F", "less": "A", "lily": "A", 
			"ness": "A", "ogen": "A", "ward": "A", "wise": "A", "ying": "B", "yish": "A" }
	
	m_l3 = {"acy": "A", "age": "B", "aic": "A", "als": "b", "ant": "B", "ars": "O", "ary": "F", 
		  	"ata": "A", "ate": "A", "eal": "Y", "ear": "Y", "ely": "E", "ene": "E", "ent": "C", 
		  	"ery": "E", "ese": "A", "ful": "A", "ial": "A", "ian": "A", "ics": "A", "ide": "L", 
		  	"ied": "A", "ier": "A", "ies": "P", "ily": "A", "ine": "M", "ing": "N", "ion": "Q", 
		  	"ish": "C", "ism": "B", "ist": "A", "ite": "a", "ity": "A", "ium": "A", "ive": "A", 
		  	"ize": "F", "oid": "A", "one": "R", "ous": "A"}
	
	m_l2 = {"ae": "A", "al": "b", "ar": "X", "as": "B", "ed": "E", "en": "F", "es": "E", "ia": "A", 
			"ic": "A", "is": "A", "ly": "B", "on": "S", "or": "T", "um": "U", "us": "V", "yl": "R", 
			"s\'": "A", "\'s": "A" }
	
	m_l1 = {"a": "A", "e": "A", "i": "A", "o": "A", "s": "W", "y": "B" }

	def _removeEnding(self, word):
		"""Finds and removes ending from given word."""
	
		el = 11
		length = len(word)
		while el > 0:
			if (length - el > 1):
				ending = word[length - el:-1]
				ml = getattr(self, "m_l%s" % el, {})
				conditionCode = ml.get(ending, None)

				if conditionCode is None:
					pass
				elif conditionCode == 'A':
					return word[0:length - el]
				elif conditionCode == 'B':
					if length - el > 2:
						return word[0:length - el]
				elif conditionCode == 'C':
					if length - el > 3:
						return word[0:length - el]
				elif conditionCode == 'D':
					if length - el > 4:
						return word[0:length - el]
				elif conditionCode == 'E':
					if word[length - el - 1] != 'e':
						return word[0:length - el]
				elif conditionCode == 'F':
					if (length - el) > 2 and word[length - el - 1] != 'e':
						return word[0:length - el]
				elif conditionCode == 'G':
					if (length - el) > 2 and word[length - el - 1] == 'f':
						return word[0:length - el]
				elif conditionCode == 'H':
					if 	word[length - el - 1] == 't' or \
	  					(word[length - el - 1] == 'l' and word[length - el - 2] == 'l'):
						return word[0:length - el]
				elif conditionCode == 'I':
					if word[length - el - 1] != 'o' and word[length - el - 1] != 'e':
						return word[0:length - el]
				elif conditionCode == 'J':
					if word[length - el - 1] != 'a' and word[length - el - 1] != 'e':
						return word[0:length - el]
				elif conditionCode == 'K':
					if 	(length - el) > 2 and \
						( (word[length - el - 1] == 'l' or word[length - el - 1] == 'i') or \
						  (word[length - el - 1] == 'e' and word[length - el - 3] == 'u')):
						return word[0:length - el]
				elif conditionCode == 'L':
					if	word[length - el - 1] != 'u' and word[length - el - 1] != 'x' and \
						(word[length - el - 1] != 's' or word[length - el - 2] == 'o'):
						return word[0:length - el]
				elif conditionCode == 'M':
					if	word[length - el - 1] != 'a' and word[length - el - 1] != 'c' and \
						word[length - el - 1] != 'e' and word[length - el - 1] != 'm':
						return word[0:length - el]
				elif conditionCode == 'N':
					if	(length - el) > 3 or \
						((length - el) == 3 and word[length - el - 3] != 's'):
						return word[0:length - el]
				elif conditionCode == 'O':
					if word[length - el - 1] == 'l' or word[length - el - 1] == 'i':
						return word[0:length - el]
				elif conditionCode == 'P':
					if word[length - el - 1] != 'c':
						return word[0:length - el]
				elif conditionCode == 'Q':
					if	(length - el) > 2 and \
						(word[length - el - 1] != 'l' and word[length - el - 1] == 'n'):
						return word[0:length - el]
				elif conditionCode == 'R':
					if word[length - el - 1] == 'n' or word[length - el - 1] == 'r':
						return word[0:length - el]
				elif conditionCode == 'S':
					if	(word[length - el - 1] == 'r' and word[length - el - 2] == 'd') or \
						(word[length - el - 1] == 't' and word[length - el - 2] != 't'):
						return word[0:length - el]
				elif conditionCode == 'T':
					if	word[length - el - 1] == 's' or \
						(word[length - el - 1] == 't' and word[length - el - 2] != 'o'):
						return word[0:length - el]
				elif conditionCode == 'U':
					if	word[length - el - 1] == 'l' or word[length - el - 1] == 'm' or \
						word[length - el - 1] == 'n' or word[length - el - 1] == 'r':
						return word[0:length - el]
				elif conditionCode == 'V':
					if word[length - el - 1] == 'c':
						return word[0:length - el]
				elif conditionCode == 'W':
					if word[length - el - 1] != 's' and word[length - el - 1] != 'u':
						return word[0:length - el]
				elif conditionCode == 'X':
					if 	word[length - el - 1] == 'l' or word[length - el - 1] != 'i' or \
	  					((length - el) > 2 and word[length - el - 1] == 'e' and word[length - el - 3] == 'u'):
						return word[0:length - el]
				elif conditionCode == 'Y':
					if word[length - el - 1] == 'n' and word[length - el - 2] != 'i':
						return word[0:length - el]
				elif conditionCode == 'Z':
					if word[length - el - 1] != 'f':
						return word[0:length - el]
				elif conditionCode == 'a':
					if 	word[length - el - 1] == 'd' or \
						word[length - el - 1] == 'f' or \
						(word[length - el - 1] == 'h' and word[length - el - 2] == 'p') or \
						(word[length - el - 1] == 'h' and word[length - el - 2] == 't') or \
	  					word[length - el - 1] == 'l' or \
						(word[length - el - 1] == 'r' and word[length - el - 2] == 'e') or \
						(word[length - el - 1] == 'r' and word[length - el - 2] == 'o') or \
						(word[length - el - 1] == 's' and word[length - el - 2] == 'e') or \
						word[length - el - 1] == 't':
						return word[0:length - el]
				elif conditionCode == 'b':
					if self.m_CompMode:
						if 	((length - el) == 3 and \
							 (not (	word[length - el - 1] == 't' and word[length - el - 2] == 'e' and \
									word[length - el - 3] =='m'))) or \
							((length - el) > 3 and \
							 (not (	word[length - el - 1] == 't' and word[length - el - 2] == 's' and \
									word[length - el - 3] == 'y' and word[length - el - 4] == 'r'))):
							return word[0:length - el]
					else:
						if 	((length - el) > 2 and \
							 (not (	word[length - el - 1] == 't' and word[length - el - 2] == 'e' and \
									word[length - el - 3] =='m'))) or \
	  						((length - el) < 4 and \
							 (not (	word[length - el - 1] == 't' and word[length - el - 2] == 's' and \
									word[length - el - 3] == 'y' and word[length - el - 4] == 'r'))):
							return word[0:length - el]
				elif conditionCode == 'c':
					if word[length - el - 1] == 'l':
						return word[0:length - el]
				else:
					raise Exception('Illegal Argument')
	
			el = el-1
		return word

	def _recodeEnding(self, word):
		"""recodes ending of given word"""	
									
		lastPos = len(word) - 1

		# Rule 1
		if 	word.endswith("bb") or \
			word.endswith("dd") or \
			word.endswith("gg") or \
			word.endswith("ll") or \
			word.endswith("mm") or \
			word.endswith("nn") or \
			word.endswith("pp") or \
			word.endswith("rr") or \
			word.endswith("ss") or word.endswith("tt"):
			word = word[0:lastPos]
			lastPos -= 1
		
		# Rule 2
		if word.endswith("iev"):
			word = word[0, lastPos - 2] + "ief"
		
		# Rule 3
		if word.endswith("uct"):
			word = word[0: lastPos - 2] + "uc"
			lastPos -= 1
		
		# Rule 4
		if word.endswith("umpt"):
			word = word[0: lastPos - 3] + "um"
			lastPos -= 2
		
		# Rule 5
		if word.endswith("rpt"):
			word = word[0: lastPos - 2] + "rb"
			lastPos -= 1

		# Rule 6
		if word.endswith("urs"):
			word = word[0: lastPos - 2] + "ur"
			lastPos -= 1
			
		# Rule 7
		if word.endswith("istr"):
			word = word[0: lastPos - 3] + "ister"
			lastPos += 1
			
		# Rule 7a
		if word.endswith("metr"):
			word = word[0: lastPos - 3] + "meter"
			lastPos += 1

		# Rule 8
		if word.endswith("olv"):
			word = word[0: lastPos - 2] + "olut"
			lastPos += 1

		# Rule 9
		if word.endswith("ul"):
			if	(lastPos -2) < 0 or \
				(word[lastPos -2] != 'a' and word[lastPos -2] != 'i' and word[lastPos -2] != 'o'): 
				word = word[0: lastPos - 1] + "l"
				lastPos -= 1
			
		# Rule 10
		if word.endswith("bex"):
			word = word[0: lastPos - 2] + "bic"
	
		# Rule 11
		if word.endswith("dex"):
			word = word[0: lastPos - 2] + "dic"
	
		# Rule 12
		if word.endswith("pex"):
			word = word[0: lastPos - 2] + "pic"
			
		# Rule 13
		if word.endswith("tex"):
			word = word[0: lastPos - 2] + "tic"

		# Rule 14
		if word.endswith("ax"):
			word = word[0: lastPos - 1] + "ac"

		# Rule 15
		if word.endswith("ex"):
			word = word[0: lastPos - 1] + "ec"
			
		# Rule 16
		if word.endswith("ix"):
			word = word[0: lastPos - 1] + "ic"

		# Rule 17
		if word.endswith("lux"):
			word = word[0: lastPos - 2] + "luc"
			
		# Rule 18
		if word.endswith("uad"):
			word = word[0: lastPos - 2] + "uas"

		# Rule 19
		if word.endswith("vad"):
			word = word[0: lastPos - 2] + "vas"
			
		# Rule 20
		if word.endswith("cid"):
			word = word[0: lastPos - 2] + "cis"

		# Rule 21
		if word.endswith("lid"):
			word = word[0: lastPos - 2] + "lis"
			
		# Rule 22
		if word.endswith("erid"):
			word = word[0: lastPos - 3] + "eris"
			
		# Rule 23
		if word.endswith("pand"):
			word = word[0: lastPos - 3] + "pans"
			
		# Rule 24
		if word.endswith("end"):
			if (lastPos - 3) < 0 or word[lastPos - 3] != 's':
				word = word[0: lastPos - 2] + "ens"

		# Rule 25
		if word.endswith("ond"):
			word = word[0: lastPos - 2] + "ons"
			
		# Rule 26
		if word.endswith("lud"):
			word = word[0: lastPos - 2] + "lus"
			
		# Rule 27
		if word.endswith("rud"):
			word = word[0: lastPos - 2] + "rus"

		# Rule 28
		if word.endswith("her"):
			if 	(lastPos - 3) < 0 or \
				(word[lastPos - 3] != 'p' and word[lastPos - 3] != 't'):
				word = word[0: lastPos - 2] + "hes"
				
		# Rule 29
		if word.endswith("mit"):
			word = word[0: lastPos - 2] + "mis"
			
		# Rule 30
		if word.endswith("end"):
			if (lastPos - 3) < 0 or word[lastPos - 3] != 'm':
				word = word[0: lastPos - 2] + "ens"
				
		# Rule 31
		if word.endswith("ert"):
			word = word[0: lastPos - 2] + "ers"
			
		# Rule 32
		if word.endswith("et"):
			if (lastPos - 2) < 0 or word[lastPos - 2] != 'n':
				word = word[0: lastPos - 1] + "es"
				
		# Rule 33
		if word.endswith("yt"):
			word = word[0: lastPos - 1] + "ys"
			
		# Rule 34
		if word.endswith("yz"):
			word = word[0: lastPos - 1] + "ys"
		
		return word

	def stem(self, word):
		word = unicode(word.lower())
		if len(word)>2:
			result = self._recodeEnding(self._removeEnding(word))
		else:
			result = word
		return result
