$package("org/mathdox/formulaeditor/semantics");

$identify("org/mathdox/formulaeditor/semantics/SemanticFloat.js");

$require("org/mathdox/formulaeditor/semantics/Node.js");
$require("org/mathdox/formulaeditor/presentation/Symbol.js");
$require("org/mathdox/formulaeditor/presentation/Row.js");

$main(function(){

  /**
  * Representation of a float in the semantic tree.
  * it is named SemanticFloat because float is a reserved keyword
  */
  org.mathdox.formulaeditor.semantics.SemanticFloat =
    $extend(org.mathdox.formulaeditor.semantics.Node, {

      /**
       * The float value.
       */
      value : null,

      /**
       * Initializes a semantic tree node to represent an float with the
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
        return "<OMF dec=\"" + this.value + "\"/>";
      },

      /**
       * See org.mathdox.formulaeditor.semantics.Node.getMathML
       */
      getMathML : function() {
        return "<mn>" + this.value + "</mn>";
      }

    });

});
