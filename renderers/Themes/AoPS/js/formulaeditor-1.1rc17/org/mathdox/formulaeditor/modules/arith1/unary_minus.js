
$identify("org/mathdox/formulaeditor/modules/arith1/unary_minus.js");

$require("org/mathdox/formulaeditor/semantics/MultaryOperation.js");
$require("org/mathdox/formulaeditor/presentation/Superscript.js");
$require("org/mathdox/formulaeditor/parsing/openmath/OpenMathParser.js");
$require("org/mathdox/formulaeditor/parsing/expression/ExpressionParser.js");

$main(function(){

  var mathmlSymbol= [ "", "", ""];
  
  if ("-" !== "") {
    mathmlSymbol[0] = "<mo>-</mo>";
  }
  if ("" !== "") {
    mathmlSymbol[2] = "<mo></mo>";
  }

  /**
   * Defines a semantic tree node that represents a unary minus.
   */
  org.mathdox.formulaeditor.semantics.Arith1Unary_minus =
    $extend(org.mathdox.formulaeditor.semantics.MultaryOperation, {
      

      symbol : {

        onscreen : ["-","",""],
        openmath : "<OMS cd='arith1' name='unary_minus'/>",
        mathml   : mathmlSymbol

      },

      precedence : 140

    });

  /**
   * Extend the OpenMathParser object with parsing code for arith1.unary_minus.
   */
  org.mathdox.formulaeditor.parsing.openmath.OpenMathParser =
    $extend(org.mathdox.formulaeditor.parsing.openmath.OpenMathParser, {

      /**
      * Returns a unary minus object based on the OpenMath node.
      */
      handleArith1Unary_minus : function(node) {

        var operand = this.handle(node.getChildNodes().item(1));
        return new org.mathdox.formulaeditor.semantics.Arith1Unary_minus(operand);

      }

    });

  /**
   * Extend the ExpressionParser object with parsing code for unary minus.
   */
  var semantics = org.mathdox.formulaeditor.semantics;
  var pG = new org.mathdox.parsing.ParserGenerator();

  var rulesEnter = [];
  var positionEnter = 0;
  if ("-" !== "") {
    rulesEnter.push(pG.literal("-"));
    positionEnter++;
  }
  rulesEnter.push(pG.rule("expression150"));
  if ("" !== "") {
    rulesEnter.push(pG.literal(""));
  }

  if (( "-"  === "-"  ) &&
      ( "" === "" )) {
    // only one expression, same on screen
    org.mathdox.formulaeditor.parsing.expression.ExpressionParser =
      $extend(org.mathdox.formulaeditor.parsing.expression.ExpressionParser, {

        // expression140 = arith1unary_minus | super.expression140
        expression140 : function() {
          var parent = arguments.callee.parent;
          pG.alternation(
            pG.rule("arith1unary_minus"),
            parent.expression140).apply(this, arguments);
        },

        // arith1unary_minus = "-" expression150 ""
        arith1unary_minus :
          pG.transform(
            pG.concatenation.apply(pG, rulesEnter),
            function(result) {
              return new semantics.Arith1Unary_minus(result[positionEnter]);
            }
          )

    });
  } else { // allow alternative as displayed on the screen
    var rulesScreen = [];
    var positionScreen = 0;
    if ("-" !== "") {
      rulesScreen.push(pG.literal("-"));
      positionScreen++;
    }
    rulesScreen.push(pG.rule("expression150"));
    if ("" !== "") {
      rulesScreen.push(pG.literal(""));
    }
  
    org.mathdox.formulaeditor.parsing.expression.ExpressionParser =
      $extend(org.mathdox.formulaeditor.parsing.expression.ExpressionParser, {

        // expression140 = arith1unary_minus | super.expression140
        expression140 : function() {
          var parent = arguments.callee.parent;
          pG.alternation(
            pG.rule("arith1unary_minus"),
            pG.rule("arith1unary_minusalt"),
            parent.expression140).apply(this, arguments);
        },

        // arith1unary_minus = "-" expression150 ""
        arith1unary_minus :
          pG.transform(
            pG.concatenation.apply(pG, rulesEnter),
            function(result) {
              return new semantics.Arith1Unary_minus(result[positionEnter]);
            }
          ),

        // arith1unary_minusalt = "-" expression150 ""
        arith1unary_minusalt :
          pG.transform(
            pG.concatenation.apply(pG, rulesScreen),
            function(result) {
              return new semantics.Arith1Unary_minus(result[positionScreen]);
            }
          )
     });
   }

});
