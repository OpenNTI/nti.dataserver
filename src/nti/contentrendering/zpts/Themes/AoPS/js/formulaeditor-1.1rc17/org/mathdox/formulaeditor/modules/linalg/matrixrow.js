$identify("org/mathdox/formulaeditor/modules/linalg/matrixrow.js");

$require("org/mathdox/formulaeditor/semantics/MultaryOperation.js");

$main(function(){
  /**
   * Define a semantic tree node that represents the linalg2.matrixrow
   */
  org.mathdox.formulaeditor.semantics.Linalg2Matrixrow =
    $extend(org.mathdox.formulaeditor.semantics.MultaryOperation, {

      symbol : {

        mathml   : ["<mtr><mtd>","</mtd><mtd>","</mtd></mtr>"],
        onscreen : ["[", ",", "]"],
        openmath : "<OMS cd='linalg2' name='matrixrow'/>"

      },

      precedence : 0

    });
});
