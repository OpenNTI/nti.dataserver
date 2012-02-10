$package("org.mathdox.formulaeditor.semantics");

$identify("org/mathdox/formulaeditor/semantics/FunctionApplication.js");

$require("org/mathdox/formulaeditor/semantics/Node.js");
$require("org/mathdox/formulaeditor/semantics/Variable.js");
$require("org/mathdox/formulaeditor/presentation/Row.js");
$require("org/mathdox/formulaeditor/presentation/Symbol.js");

$main(function(){

  /**
   * Representation of an n-ary function application.
   */
  org.mathdox.formulaeditor.semantics.FunctionApplication =
    $extend(org.mathdox.formulaeditor.semantics.Node, {

      /**
       * The operands of the operation.
       */
      operands: null,
      
      /**
       * Information about the style
       * style="sub" means presentation should be subscript
       */
      style: null,
      /**
       * Information about the symbol that is used to represent this operation.
       */
      symbol: null,

      /**
       * Initializes the operation using the specified arguments as operands.
       */
      initialize : function(symbol, operands, style) {
        this.symbol = symbol;
        this.operands = operands;
        if (style !== undefined) {
          this.style = style;
        }
      },

      /**
       * See org.mathdox.formulaeditor.semantics.Node.getPresentation(context)
       */
      getPresentation : function(context) {

        var presentation = org.mathdox.formulaeditor.presentation;

        // construct an array of the presentation of operand nodes interleaved
        // with operator symbols
        var array = [];
        var pres;

        array.push(this.symbol.getPresentation(context));
        if (this.style != "sub") {
          // no brackets in subscript style "sub"
          array.push(new presentation.Symbol("("));
        }
        for (var i=0; i<this.operands.length; i++) {
          var operand = this.operands[i];
          if (i>0) {
            pres = new presentation.Symbol(",");
            if (this.style == "sub") {
              // subscript style
              array.push(new presentation.Subscript(pres));
            } else {
              // normal style
              array.push(pres);
            }

          }
          
          if (!operand) {
            alert("symbol: "+this.symbol.symbol.onscreen);
            alert("operands.length: "+this.operands.length);
            alert("operands[0]: "+this.operands[0]);
            alert("operands[1]: "+this.operands[1]);
          }
          pres = operand.getPresentation(context);
          if (this.style == "sub") {
            // subscript style
            array.push(new presentation.Subscript(pres));
          } else {
            // normal style
            array.push(pres);
          }
        }
        
        if (this.style != "sub") {
          // no brackets in subscript style "sub"
          array.push(new presentation.Symbol(")"));
        }

        // create and return new presentation row using the constructed array
        var result = new presentation.Row();
        result.initialize.apply(result, array);

        return result;

      },

      /**
       * See org.mathdox.formulaeditor.semantics.Node.getOpenMath()
       */
      getOpenMath : function() {

        var result;
	
	if (this.style !== null) {
	  result = "<OMA style=\""+this.style+"\">";
	} else {
	  result = "<OMA>";
	}

	result += this.symbol.getOpenMath();
        for (var i=0; i<this.operands.length; i++) {
          result = result + this.operands[i].getOpenMath();
        }
        result = result + "</OMA>";

        return result;

      },

      /**
       * See org.mathdox.formulaeditor.semantics.Node.getMathML()
       */
      getMathML : function() {

        var result = "<mrow>" + this.symbol.getMathML() + "<mo>(</mo>";

        for (var i=0; i<this.operands.length; i++) {
	  if (i>0) {
	    result = result + "<mo>,</mo>";
	  }
          result = result + this.operands[i].getMathML();
        }
        result = result + "<mo>)</mo>" + "</mrow>";

        return result;

      }

    });

});
