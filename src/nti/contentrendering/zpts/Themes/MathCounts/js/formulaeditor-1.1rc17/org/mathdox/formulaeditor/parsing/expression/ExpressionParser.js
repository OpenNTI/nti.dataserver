$package("org.mathdox.formulaeditor.parsing.expression");

$identify("org/mathdox/formulaeditor/parsing/expression/ExpressionParser.js");

$require("org/mathdox/parsing/Parser.js");
$require("org/mathdox/parsing/ParserGenerator.js");
$require("org/mathdox/formulaeditor/parsing/expression/KeywordList.js");
$require("org/mathdox/formulaeditor/presentation/Subscript.js");
$require("org/mathdox/formulaeditor/semantics/FunctionApplication.js");
$require("org/mathdox/formulaeditor/semantics/Integer.js");
$require("org/mathdox/formulaeditor/semantics/SemanticFloat.js");
$require("org/mathdox/formulaeditor/semantics/Variable.js");

$main(function() {

  var semantics = org.mathdox.formulaeditor.semantics;
  var pG = new org.mathdox.parsing.ParserGenerator();

    org.mathdox.formulaeditor.parsing.expression.ExpressionParser =
      $extend(org.mathdox.parsing.Parser, {
        // TODO make this list alphabetical

        // start = expression
        start : pG.rule("expression"),

        // expression = expression70
        expression  : pG.rule("expression70"), 

        // expression70 = expression80
        expression70 : pG.rule("expression80"), // equivalence, ...

        // expression80 = expression90
        expression80 : pG.rule("expression90"), // implies, ...

        // expression90 = expression100
        expression90 : pG.rule("expression100"), // or, ...

        // expression100 = expression110
        expression100 : pG.rule("expression110"), // and, ...

        // expression110 = expression120
	expression110 : pG.rule("expression120"), // equals, lessthan,
						  // morethan, ...

        // expression120 = expression130
        expression120 : pG.rule("expression130"), // plus, minus

        // expression130 = expression140
        expression130 : pG.rule("expression140"), // times

        // expression140 = expression150
        expression140 : pG.rule("expression150"), // unary minus

        // expression150 = expression160
        expression150 : pG.rule("expression160"), // power

        // expression160 = braces | integer | variable
        expression160 :
          pG.alternation(
            pG.rule("braces"),
            pG.rule("parseNumber"),
            pG.rule("func"),
            pG.rule("func_sub"),
            pG.rule("variable"),
            pG.rule("omSymbol"),
            pG.rule("omString")
          ),

        // restrictedexpression160 = braces | variable | func
        // no number allowed, for silent multiplication
        restrictedexpression160 :
          pG.alternation(
            pG.rule("braces"),
            pG.rule("func"),
            pG.rule("func_sub"),
            pG.rule("variable"),
            pG.rule("omSymbol")
          ),

        // integer = [0..9]+
        integer :
          pG.transform(
            pG.repetitionplus(
              pG.range('0','9')
            ),
            function(result) {
              return new semantics.Integer(Number(result.join("")));
            }
          ),

        // float = [0..9]+ ++ '.' ++ [0-9]*
        parseFloat :
          pG.transform(
            pG.concatenation( 
              pG.repetitionplus(
                pG.range('0','9')
              ),
              pG.literal('.'),
              pG.repetition(
                pG.range('0','9')
              )
            ),
            function(result) {
              return new semantics.SemanticFloat(Number(result.join("")));
            }
          ),

        // number: float | integer
        parseNumber :
          pG.alternation(
            pG.rule("parseFloat"),
            pG.rule("integer")
          ),

        // variable = ([a..z]|[A..Z]) ([a..z]|[A..Z]|[0..9])*
        variable :
          pG.transform(
            pG.concatenation(
              pG.alternation(
                pG.range('a','z'),
                pG.range('A','Z')
              ),
              pG.repetition(
                pG.alternation(
                  pG.range('a','z'),
                  pG.range('A','Z'),
                  pG.range('0','9')
                )
              )
            ),
            function(result) {
              // store result.join(""); in a variable since it is used twice
              var result_joined=result.join("");

              if (org.mathdox.formulaeditor.parsing.expression.KeywordList[
                      result_joined] === undefined ||
		  org.mathdox.formulaeditor.parsing.expression.KeywordList[
		      result_joined] === null) {
                // not in the list of variables that are symbols
                return new semantics.Variable(result_joined);
              } else {
                // in the list of symbols, return the corresponding object
                // instead
                // TODO: check if we need to update the presentation tree
                return org.mathdox.formulaeditor.parsing.expression.KeywordList[result_joined];
              }
            }
          ),
        // omString = "([a..z]|[A..Z]|[0..9]|' _.-')*"
        // TODO: maybe add more symbols
        omString:
          pG.transform(
            pG.concatenation(
              pG.literal('"'),
              pG.repetitionplus( 
                pG.alternation(
                  pG.range('a','z'),
                  pG.range('A','Z'),
                  pG.range('0','9'),
                  pG.literal(' '),
                  pG.literal('_'),
                  pG.literal('.'),
                  pG.literal('-')
                )
              ),
              pG.literal('"')
            ),
            function(result) {
              return new semantics.SString(result.slice(1,result.length-1).join(""));
            }
          ),
        
        // omSymbol = ([a..z]|[A..Z]) ([a..z]|[A..Z]|[0..9]|'_')* '.' ([a..z]|[A..Z])([a..z]|[A..Z]|[0..9]|_)*
        omSymbol:
          pG.transform(
            pG.concatenation(
              pG.alternation(
                pG.range('a','z'),
                pG.range('A','Z')
              ),
              pG.repetition(
                pG.alternation(
                  pG.range('a','z'),
                  pG.range('A','Z'),
                  pG.range('0','9'),
                  pG.literal('_')
                )
              ),
              pG.literal('.'),
              pG.alternation(
                pG.range('a','z'),
                pG.range('A','Z')
              ),
              pG.repetition(
                pG.alternation(
                  pG.range('a','z'),
                  pG.range('A','Z'),
                  pG.range('0','9'),
                  pG.literal('_')
                )
              )
            ),

            /* 
             * XXX: hard to check whether something is a constant or a function
             */
            function(result) {
              var symbolinfo = result.join("").split('.');
              var cd=symbolinfo[0];
              var name=symbolinfo[1];

              var symbol = {
                onscreen: null,
                openmath: null,
                mathml: "&lt;mi&gt;"+cd+"."+name+"&lt;/mi&gt;"
              };
              return new semantics.Keyword(cd,name,symbol,"constant");
            }
          ),

        // braces = '(' expression ')'
        braces :
          pG.transform(
            pG.concatenation(
              pG.literal('('),
              pG.rule("expression"),
              pG.literal(')')
            ),
            function(result) {
	      result[1].inside_braces = true;
              return result[1];
            }
          ),

        // function = variable '(' expr ( ',' expr ) * ')'
        func :
          pG.transform(
            pG.concatenation(
              pG.alternation(
                pG.rule("variable"),
                pG.rule("omSymbol"),
                pG.rule("braces"),
                pG.rule("func_sub")
              ),
              pG.repetitionplus(
                pG.concatenation(
                  pG.literal('('),
                  pG.rule("expression"),
                  pG.repetition(
                    pG.concatenation(
                      pG.literal(","),
                      pG.rule("expression")
                    )
                  ),
                  pG.literal(')')
                )
              )
            ),
            function(result) {
              var array;
              var i,j; // counters
              
              var oper = result[0];
              
              var str;

              i=1;
              while (i < result.length) {
                // current position = '('
                array = [];
                i++;
                // current position should be a variable
                while (i<result.length && result[i] != ')') {
                  // function argument
                  array.push(result[i]);
                  i++;

                  if (i<result.length && result[i]==',') {
                    // comma -> skip
                    i++;
                  }
                }
                // current position should be ')'
                if (oper.parseResultFun !== undefined) {
                  // special case: result function in operation
                  oper = oper.parseResultFun(oper, array);
                } else {
                  oper = new org.mathdox.formulaeditor.semantics.FunctionApplication(oper, array);
                }

                i++;
              }

              return oper;
            }
          ),
        func_sub:
          pG.transform(
            pG.concatenation(
              pG.alternation(
                pG.rule("variable"),
                pG.rule("omSymbol"),
                pG.rule("braces")
              ),
              pG.repetitionplus(
                pG.alternation(
                  pG.concatenation(
                    pG.literal('_'),
                    pG.alternation(
                      pG.rule("variable"),
                      pG.rule("omSymbol"),
                      pG.rule("integer"),
                      pG.concatenation(
                        pG.literal('{'),
                        pG.rule("expression"),
                        //repetition(
                        //  concatenation(
                        //    literal(","),
                        //    rule("expression")
                        //  )
                        //),
                        pG.literal('}')
                      )
                    )
                  ),
                  pG.rule("subscript")
                )
              )
            ),
            function(result) {
              var array;
              var i,j; // counters
              var semantics = org.mathdox.formulaeditor.semantics;
              
              var oper = result[0];
              var str;

              i=1;
              while (i < result.length) {
                // current position == '_' (or subscript)
                if (result[i]== "_") {
                  // current position == '_'
                  i++;
                }

                if (i<result.length && result[i] != '{') {
                  // simple argument
                  oper = new semantics.FunctionApplication(oper, [result[i]], 
                    "sub");
                  i++;
                  // current position == '_', subscript or end
                } else {
                  i++;
                  // current position: first argument
                  array = [];
                  // current position should be an argument
                  while (i<result.length && result[i] != '}') {
                    // function argument
                    array.push(result[i]);
                    i++;

                    if (i<result.length && result[i]==',') {
                      // comma -> skip
                      i++;
                    }
                  }
                  // current position should be '}'
                  oper = new semantics.FunctionApplication(oper, array, "sub");

                  i++;
                  // current position == '_', subscript or end
                }
              }

              return oper;
            }
          ),
          // subscript : rule only occurs from presentation
          subscript: pG.never
        
      });

  }

);
