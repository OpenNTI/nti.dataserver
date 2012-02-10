$package("org.mathdox.formulaeditor.presentation");

$identify("org/mathdox/formulaeditor/presentation/Symbol.js");

$require("org/mathdox/formulaeditor/presentation/Node.js");

$main(function(){

  /**
   * Representation of a mathematical symbol (number, letter, operator) in the
   * presentation tree.
   */
  org.mathdox.formulaeditor.presentation.Symbol =
    $extend(org.mathdox.formulaeditor.presentation.Node, {

      /**
       * A string representation of the symbol.
       */
      value : null,
      /**
       * A string representation of the symbol for on the screen
       */
      onscreen : null,
      /**
       * The typeface (currently supported: math, which means display as
       * slanted if possible)
       */
      typeface : null,

      /**
       * Initializes a Symbol node in the presentation tree using the specified
       * string representation of a symbol.
       */
      initialize : function() {
        
        if (arguments.length > 0) {
          if (arguments[0] instanceof Array) {
            this.value = arguments[0][0];
            if (arguments[0].length > 1) {
              this.onscreen = arguments[0][1];
            }
          } else {
            this.value = arguments[0];
          }
        }
        if (arguments.length > 1) {
          this.typeface = arguments[1];
        }
      },

      /**
       * Draws the symbol to the canvas.
       *
       * See also: org.mathdox.formulaeditor.presentation.Node.draw
       */
      draw : function(canvas, x, y, invisible) {
        var symbol = this.value;
        if (this.onscreen !== null) {
          symbol = this.onscreen;
        }
       
        this.dimensions = canvas.drawSymbol(
          symbol, Math.round(x), Math.round(y), invisible, this.typeface);

        return this.dimensions;

      }

    });

});
