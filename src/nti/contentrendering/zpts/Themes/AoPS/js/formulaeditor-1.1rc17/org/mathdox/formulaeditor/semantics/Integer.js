$package("org/mathdox/formulaeditor/semantics");

$identify("org/mathdox/formulaeditor/semantics/Integer.js");

$require("org/mathdox/formulaeditor/semantics/Node.js");
$require("org/mathdox/formulaeditor/presentation/Symbol.js");
$require("org/mathdox/formulaeditor/presentation/Row.js");

$main(function(){

  /**
  * Representation of an integer in the semantic tree.
  */
  org.mathdox.formulaeditor.semantics.Integer =
    $extend(org.mathdox.formulaeditor.semantics.Node, {

      /**
       * The integer value.
       */
      value : null,

      /**
       * Initializes a semantic tree node to represent an integer with the
       * specified value.
       */
      initialize : function(value) {
        this.value = value;
      },

      /**
       * See org.mathdox.formulaeditor.semantics.Node.getPresentation
       */
      getPresentation : function(context) {
        var presentation = org.mathdox.formulaeditor.presentation;

        var string = this.value.toString();
        var symbols = [];

        for (var i=0; i<string.length; i++) {
          symbols[i] = new presentation.Symbol(string.charAt(i));
        }

        var result = new presentation.Row();
        result.initialize.apply(result, symbols);
        return result;

      },

      /**
       * See org.mathdox.formulaeditor.semantics.Node.getOpenMath
       */
      getOpenMath : function() {
        return "<OMI>" + this.value + "</OMI>";
      },

      /**
       * See org.mathdox.formulaeditor.semantics.Node.getMathML
       */
      getMathML : function() {
        return "<mn>" + this.value + "</mn>";
      }

    });

});
