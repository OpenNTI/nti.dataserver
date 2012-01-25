$package("org.mathdox.formulaeditor.semantics");

$identify("org/mathdox/formulaeditor/semantics/Keyword.js");

$require("org/mathdox/formulaeditor/semantics/Node.js");
$require("org/mathdox/formulaeditor/presentation/Symbol.js");

$main(function(){

  /**
   * Representation of a keyword.
   */
  org.mathdox.formulaeditor.semantics.Keyword =
    $extend(org.mathdox.formulaeditor.semantics.Node, {

      /**
       * The operands of the operation.
       */
      operands: null,

      /**
       * Information about the symbol that is used to represent this keyword.
       */
      symbol : {

        /**
         * The symbol(s) that is/are used for rendering the keyword to the
         * screen.
         */
        onscreen : null,

        /**
         * The OpenMath symbol that is associated with this operation.
         */
        openmath : null,

        /**
         * The MathML representation of this operation.
         */
        mathml   : null

      },

      /**
       * Initializes the keyword using the specified arguments as operands.
       * type should be one of the following strings:
       *
       * "constant" : constant like nums1.pi which probably cannot have
       *    arguments 
       * "function" : function like transc1.sin which probably should have
       *    arguments
       * "infix"    : infix operator like arith1.plus which can only occur
       *    without arguments in special places like an editor1.palette_row
       */
      initialize : function(cd,name,symbol,type) {
        this.cd = cd;
        this.name = name;
        this.type = type;

        if (symbol) {
          this.symbol = {};
          if (symbol.onscreen) {
            this.symbol.onscreen = symbol.onscreen;
          }
          if (symbol.openmath) {
            this.symbol.openmath = symbol.openmath;
          }
          if (symbol.mathml) {
            this.symbol.mathml = symbol.mathml;
          }
        }
      },

      /**
       * See org.mathdox.formulaeditor.semantics.Node.getPresentation(context)
       */

      getPresentation : function(context) {
        var presentation = org.mathdox.formulaeditor.presentation;
        var string;

        // XXX make case distinction for U+25A1 white square 
        // to become BlockSymbol
        if (this.symbol.onscreen !== null && this.symbol.onscreen!== undefined) {
          // U+25A1 white square
          if (this.symbol.onscreen == '□') {
            if (context.inPalette === true && 
              (context.inMatrix === true || context.inVector === true)
            ) {
              return new presentation.Row(new presentation.BlockSymbol(','));
            } else {
              return new presentation.Row(new presentation.BlockSymbol());
            }
          } else if (this.symbol.onscreen === '') {
            if (context.inPalette === true) {
              string=" ";
            } else {
              string=" ";
            }
          } else {
            string = this.symbol.onscreen.toString();
          }
        } else {
          string = (this.cd + "." + this.name).toString();
        }

        var symbols = [];

        for (var i=0; i<string.length; i++) {
          symbols[i] = new presentation.Symbol(string.charAt(i));
        }

        var result = new presentation.Row();
        result.initialize.apply(result, symbols);
        return result;
      },

      /**
       * See org.mathdox.formulaeditor.semantics.Node.getOpenMath()
       */
      getOpenMath : function() {
        var result;
        
        if (this.symbol.openmath !== null 
	    && this.symbol.openmath !== undefined) {
          result = this.symbol.openmath;
        } else {
          result = "<OMS cd='" + this.cd + "' name='" + this.name + "'/>";
        }
        return result;
      },

      /**
       * See org.mathdox.formulaeditor.semantics.Node.getMathML()
       */
      getMathML : function() {
        var result;
        
        if (this.symbol.mathml !== null) {
          result = this.symbol.mathml;
        } else if (this.symbol.onscreen !== null) {
          result = "<mi>" + this.symbol.onscreen + "</mi>";
        } else {
          result = "<mi>" + this.cd + "." + this.name + "</mi>";
        }

        return result;
      }

    });

});
