$package("org.mathdox.formulaeditor.semantics");

$identify("org/mathdox/formulaeditor/semantics/Node.js");


$main(function(){

  /**
   * Representation of a node in the semantic tree.
   */
  org.mathdox.formulaeditor.semantics.Node = $extend(Object, {

    /**
     * Returns the presentation tree node that is used to draw this semantic
     * tree node on a canvas. This is an abstract method, so it is expected that
     * subclasses will override this method.
     *
     * context: object that can contain information that might influence the
     * presentation of child objects. context cascades; it is either the same,
     * or copied and then extended or modified.
     */
    getPresentation : function(context) {
      throw new Error("abstract method called");
    },

    /**
     * Returns the OpenMath representation of the node. This is an abstract
     * method, so it is expected that subclasses will override this method.
     */
    getOpenMath : function() {
      throw new Error("abstract method called");
    },

    /**
     * Returns the MathML presentation of the node. This is an abstract method,
     * so it is expected that subclasses will override this method.
     */
    getMathML : function() {
      throw new Error("abstract method called");
    }

  });

});
