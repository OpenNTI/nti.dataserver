$identify("org/mathdox/formulaeditor/modules/arithmetic/root.js");

$require("org/mathdox/formulaeditor/semantics/MultaryOperation.js");
$require("org/mathdox/formulaeditor/presentation/Root.js");
$require("org/mathdox/formulaeditor/parsing/openmath/OpenMathParser.js");
$require("org/mathdox/formulaeditor/parsing/expression/ExpressionParser.js");

$main(function(){

  /**
   * Defines a semantic tree node that represents a root.
   */
  org.mathdox.formulaeditor.semantics.Arith1Root =
    $extend(org.mathdox.formulaeditor.semantics.MultaryOperation, {

      symbol : {

        openmath : "<OMS cd='arith1' name='root'/>"

      },

      precedence : 160,

      getPresentation : function(context) {

        var presentation = org.mathdox.formulaeditor.presentation;

        return new presentation.Row(new presentation.Root(
          this.operands[0].getPresentation(context),
          this.operands[1].getPresentation(context)
        ));
      },

      getMathML : function() {

        return "<msqrt>" +
          this.operands[0].getMathML()+
          "</msqrt>";

      }

  });

  /**
  * Extend the OpenMathParser object with parsing code for arith1.divide.
  */
  org.mathdox.formulaeditor.parsing.openmath.OpenMathParser =
    $extend(org.mathdox.formulaeditor.parsing.openmath.OpenMathParser, {

      /**
      * Returns a Root object based on the OpenMath node.
      */
      handleArith1Root : function(node) {

        // parse the left and right operands
        var children = node.getChildNodes();
        var middle  = this.handle(children.item(1));
        var base  = this.handle(children.item(2));

        // construct a root object
        return new org.mathdox.formulaeditor.semantics.Arith1Root(middle, base);

      }

  });

  /**
   * Extend the ExpressionParser object with parsing code for division.
   */
  var pG = new org.mathdox.parsing.ParserGenerator();

  org.mathdox.formulaeditor.parsing.expression.ExpressionParser =
    $extend(org.mathdox.formulaeditor.parsing.expression.ExpressionParser, {

      // expression160 = root | super.expression160
      expression160 : function() {
        var parent = arguments.callee.parent;
        pG.alternation(
          pG.rule("root"),
          parent.expression160).apply(this, arguments);
      },

      // root = never
      root : pG.never

  });

});
