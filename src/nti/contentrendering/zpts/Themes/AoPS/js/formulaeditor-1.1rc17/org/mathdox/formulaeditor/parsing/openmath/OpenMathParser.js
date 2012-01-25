$package("org.mathdox.formulaeditor.parsing.openmath");

$identify("org/mathdox/formulaeditor/parsing/openmath/OpenMathParser.js");

$require("org/mathdox/formulaeditor/parsing/openmath/KeywordList.js");
$require("org/mathdox/formulaeditor/parsing/openmath/VariableList.js");
$require("org/mathdox/formulaeditor/semantics/FunctionApplication.js");
$require("org/mathdox/formulaeditor/semantics/Integer.js");
$require("org/mathdox/formulaeditor/semantics/SemanticFloat.js");
$require("org/mathdox/formulaeditor/semantics/String.js");
$require("org/mathdox/formulaeditor/semantics/Variable.js");

var SAXDriver;
$require("net/sf/xmljs/xmlsax.js", function() { return SAXDriver; });

var DOMImplementation;
$require("net/sf/xmljs/xmlw3cdom.js", function() { return DOMImplementation; });

$main(function(){

  org.mathdox.formulaeditor.parsing.openmath.OpenMathParser = $extend(Object, {

    /**
     * Parses the supplied OpenMath xml, and returns a
     * org.mathdox.formulaeditor.semantics.Node.
     */
    parse: function(xml) {

      var rootnode = new DOMImplementation().loadXML(xml).getDocumentElement();

      /* remove comment nodes, since we don't want to parse them */
      if (rootnode !== null) {
        this.removeComments(rootnode);
      } else {
        return null;
      }
      
      /* do the actual parsing */
      if (rootnode !== null) {
        return this.handle(rootnode);
      }
      else {
        return null;
      }

    },

    /**
     * Extracts the local name of the node, and uses that to figure out which
     * method should be called to handle this node. For instance, when an
     * <OMI> node is encountered, the handleOMI method is called.
     */
    handle: function(node) {
      if (node.getLocalName()==="") {
        // XML comment
        return null;
      }

      var handler = "handle" + node.getLocalName();

      if (handler in this) {
        return this[handler](node);
      }
      else {
        throw new Error( "OpenMathParser doesn't know how to handle this "+
            "node: " + node +". INFO: 1.");
      }

    },

    /**
     * Handles an <OMOBJ> node by processing its child node.
     */
    handleOMOBJ: function(node) {

      var child = node.getFirstChild();
      if (child !== null) {
        return this.handle(child);
      }
      else {
        return null;
      }

    },

    /**
     * Handle an <OMA> node.
     */
    handleOMA: function(node) {
      var symbol;
      var semantics = org.mathdox.formulaeditor.semantics;

      var style = node.getAttribute("style");

      // handle <OMA>'s with as first argument an <OMS/>
      if ("OMS" == node.getFirstChild().getLocalName()) {

        // helper function that uppercases first character of provided string
        var uppercase = function(string) {
            return string.substring(0,1).toUpperCase() + string.substring(1);
        };

        // figure out which handler method to call; for instance, for handling 
        // an <OMA> with as first argument <OMS cd='arith1' name='plus'/>, the
        // handleArith1Plus method is called
        var symbolname= node.getFirstChild().getAttribute("cd") + "__" + node.getFirstChild().getAttribute("name");

        var handler = "handle";

        handler += uppercase(node.getFirstChild().getAttribute("cd"));
        handler += uppercase(node.getFirstChild().getAttribute("name"));

        // call the handler method
        if (handler in this) {
          return this[handler](node, style);
        } else if (org.mathdox.formulaeditor.parsing.openmath.KeywordList[symbolname] !== null && org.mathdox.formulaeditor.parsing.openmath.KeywordList[symbolname] !== undefined) {
          /* return a FunctionApplication at the end */
          symbol = this.handleOMS(node.getFirstChild());
        } else {
          var cd = node.getFirstChild().getAttribute("cd");
          var name = node.getFirstChild().getAttribute("name");
          var keywordsymbol = {
            onscreen : null,
            openmath : null,
            mathml: "<mi>"+cd+"."+name+"</mi>"
          };
          symbol = new semantics.Keyword(cd, name, keywordsymbol, "function");
        }

      } else if ("OMV" == node.getFirstChild().getLocalName()) {
        /* return a FunctionApplication at the end */
        symbol = this.handleOMV(node.getFirstChild());
      } else if ("OMA" == node.getFirstChild().getLocalName()) {
        symbol = this.handleOMA(node.getFirstChild());
      } else {
        throw new Error(
          "OpenMathParser doesn't know how to handle an <OMA> that does " +
          "not have an <OMS/> or <OMV/> as first argument");

      }

      if (symbol) {
        var children = node.getChildNodes();
        var operands = [];

        for (var i=1; i<children.length; i++) {
          var child = this.handle(children.item(i));

          if (child !== null) { 
            // ignore comments
            operands.push(child);
          }
        }
       
        if (style !== "" && style !== null) {
          return new semantics.FunctionApplication(symbol, operands, style);
        } else {
          return new semantics.FunctionApplication(symbol, operands);
        }
      }
    },

    /**
     * Handles an <OMBIND> node by pretending its an <OMA> node.
     */
    handleOMBIND: function(node) {

      return this.handleOMA(node);

    },

    /**
     * Ignores an <OMBVAR> node.
     */
    handleOMBVAR: function(node) {

      return this.handle(node.getFirstChild());

    },

    /**
     * Handles an <OMF> node.
     */
    handleOMF: function(node) {

      var semantics = org.mathdox.formulaeditor.semantics;
      if (node.getAttribute("dec")) {
        return new semantics.SemanticFloat(node.getAttribute("dec"));
      }

    },

    /**
     * Handles an <OMI> node.
     */
    handleOMI: function(node) {

      var semantics = org.mathdox.formulaeditor.semantics;
      return new semantics.Integer(node.getFirstChild().getNodeValue());

    },

    /**
     * Handles an <OMS> node that is translated to a symbol without arguments
     */
    handleOMS: function(node) {
      var symbolname= node.getAttribute("cd") + "__" + node.getAttribute("name");
      var keyword = org.mathdox.formulaeditor.parsing.openmath.KeywordList[symbolname];

      if (keyword !== null && keyword !== undefined) {
        if (keyword.type == "constant" || keyword.type == "function") {
          return keyword;
        } else if (keyword.type == "infix") {
          //check if parent is palette_row
          var error = false; // set to true if an error is found
          var parentNode = node.getParentNode();
          var omsNode = parentNode.getFirstChild();
          if (omsNode.getLocalName()!="OMS") {
            throw new Error(
              "OpenMathParser doesn't know how to handle this keyword of unknown type ("+keyword.type+"): " + node + " when it is not first in an <OMA>. First sibling is "+ omsNode.getLocalName()+".");
          }
          if (omsNode.getAttribute("cd")=="editor1" && 
            omsNode.getAttribute("name")=="palette_row") {
            // inside a palette_row -> return the found infix symbol
            return keyword;
          } else {
            throw new Error(
              "OpenMathParser doesn't know how to handle this keyword of unknown type ("+keyword.type+"): " + node + " when it is not first in an <OMA>. INFO: was expecting symbol reference 'editor1.palette_row' instead found '"+omsNode.getAttribute("cd")+"."+omsNode.getAttribute("name")+"'.");
          }

        } else {
          throw new Error(
            "OpenMathParser doesn't know how to handle this keyword of unknown type ("+keyword.type+"): " + node + " when it is not first in an <OMA>.");
        }
      } else {
        var semantics = org.mathdox.formulaeditor.semantics;
        var cd = node.getAttribute("cd");
        var name = node.getAttribute("name");
        var keywordsymbol = {
          onscreen : null,
          openmath : null,
          mathml: "<mi>"+cd+"."+name+"</mi>"
        };
        return new semantics.Keyword(cd, name, keywordsymbol, "constant");
      }
    },

    /**
     * Handles an <OMSTR> node.
     */
    handleOMSTR: function(node) {
      var semantics = org.mathdox.formulaeditor.semantics;
      var children = [];
      var name="";
      var i;
      var child;
      for (i=0;i<node.childNodes.length; i++) {
	child = node.childNodes.item(i);
        if (child.nodeType == 3) { // Node.TEXT_NODE
	  children.push(child.nodeValue);
	}
      }
      return new semantics.SString(children.join(""));
    },
    /**
     * Handles an <OMV> node.
     */
    handleOMV: function(node) {

      var semantics = org.mathdox.formulaeditor.semantics;
      var varname= node.getAttribute("name");
      var variable = org.mathdox.formulaeditor.parsing.openmath.VariableList[varname];

      if (variable !== null && variable !== undefined) {
	return variable;
      } else {
      	return new semantics.Variable(varname);
      }

    },
    /**
     * Removes all comment nodes from a DOM XML tree
     */
    removeComments: function(node) {
      var children = node.getChildNodes();

      for (var i=children.length - 1; i>=0; i--) {
        var child = children.item(i);

        if (child) {
          if (child.getNodeType() == DOMNode.COMMENT_NODE) {
            node.removeChild(child);
          } else if (child.hasChildNodes()) {
            this.removeComments(child);
          }
        }
      }
    }

  });

});
