$package("org.mathdox.formulaeditor.presentation");

$identify("org/mathdox/formulaeditor/presentation/Matrix.js");

$require("org/mathdox/formulaeditor/presentation/Bracket.js");
$require("org/mathdox/formulaeditor/presentation/Bracketed.js");
$require("org/mathdox/formulaeditor/presentation/PArray.js");
$require("org/mathdox/formulaeditor/modules/linalg/matrixrow.js");

$main(function(){

  /**
   * Representation of a column of mathematical expressions in the presentation
   * tree.
   */
  org.mathdox.formulaeditor.presentation.Matrix =
    $extend(org.mathdox.formulaeditor.presentation.Bracketed, {
      // variable to store the array to get the semantics
      pArray : null,

      initialize : function () {
        var presentation = org.mathdox.formulaeditor.presentation;
        var leftBracket = new presentation.Bracket('(');
        var rightBracket = new presentation.Bracket(')');

        this.pArray = new presentation.PArray();
          
        this.pArray.initialize.apply(this.pArray,arguments);
        this.pArray.margin = 10.0;

        arguments.callee.parent.initialize.call(this, leftBracket,
          this.pArray, rightBracket);
      },

      getSemantics : function() {
        var rows = this.pArray.entries; // this.middle is the pArray
        var semanticRows;
        var matrix;

        var semantics = org.mathdox.formulaeditor.semantics;
        semanticRows = [];
        for (var i=0;i<rows.length;i++) {
          var semanticRowEntries;

          semanticRowEntries = [];
          for (var j=0; j<rows[i].length;j++) {
            semanticRowEntries.push(rows[i][j].getSemantics().value);
          }
          var semanticRow = new semantics.Linalg2Matrixrow();
          semanticRow.initialize.apply(semanticRow, semanticRowEntries);
          semanticRows.push(semanticRow);
        }
        matrix = new semantics.Linalg2Matrix();
        matrix.initialize.apply(matrix, semanticRows);

        return {
          value : matrix,
          rule  : "braces"
        };
      }

    });

});
