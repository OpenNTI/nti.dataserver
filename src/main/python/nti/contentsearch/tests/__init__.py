from whoosh import fields

##########################

phrases = (	"Yellow brown", "Blue red green render purple?",\
			"Alpha beta", "Gamma delta epsilon omega.",\
			"One two", "Three rendered four five.",\
			"Quick went", "Every red town.",\
			"Yellow uptown",  "Interest rendering outer photo!",\
			"Preserving extreme", "Chicken hacker")

domain = (	"alfa", "bravo", "charlie", "delta", "echo", "foxtrot",
			"golf", "hotel", "india", "juliet", "kilo", "lima", "mike",
			"november", "oscar", "papa", "quebec", "romeo", "sierra",
			"tango", "uniform", "victor", "whiskey", "xray", "yankee",
			"zulu")


sample_schema = fields.Schema(	id=fields.ID(stored=True, unique=True),\
								content=fields.TEXT(stored=True))
