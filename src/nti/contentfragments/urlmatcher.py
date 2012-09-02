from __future__ import print_function, unicode_literals

import re

# http://daringfireball.net/2010/07/improved_regex_for_matching_urls

grubber_v1 = u"""(
                  (?:
                    [a-z][\w-]+:
                    (?:
                      /{1,3}
                      |
                      [a-z0-9%]
                    )
                    |
                    www\d{0,3}[.]
                    |
                    [a-z0-9.\-]+[.][a-z]{2,4}/
                  )
                  (?:
                    [^\s()<>]+
                    |
                    \(([^\s()<>]+|(\([^\s()<>]+\)))*\)
                  )+
                  (?:
                    \(([^\s()<>]+|(\([^\s()<>]+\)))*\)
                    |
                    [^\s`!()\[\]{};:'".,<>?гхрсту]
                  )
                )"""

grubber_v2 = u"""(				   
				(?:
					https?://			   
					|					   
					www\d{0,3}[.]		   
					|						  
					[a-z0-9.\-]+[.][a-z]{2,4}/ 
				  )
				  (?:					 
					[^\s()<>]+				 
					|						  
					\(([^\s()<>]+|(\([^\s()<>]+\)))*\) 
				  )+
				  (?:					   
					\(([^\s()<>]+|(\([^\s()<>]+\)))*\) 
					|							   
					[^\s`!()\[\]{};:'\".,<>?гхрсту]
				  )
				)"""
        
def _create_grubber_pattern(pattern, flags=re.I | re.U):
    return re.compile(pattern.replace('\t', '').replace('\n','').replace(' ', ''), flags)
    
grubber_v1_pattern = _create_grubber_pattern(grubber_v1)
grubber_v2_pattern = _create_grubber_pattern(grubber_v2)