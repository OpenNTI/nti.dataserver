$package("org.mathdox.formulaeditor.presentation");

$identify("org/mathdox/formulaeditor/presentation/Root.js");

$require("org/mathdox/formulaeditor/modules/keywords.js");

$require("org/mathdox/formulaeditor/presentation/Bracket.js");
$require("org/mathdox/formulaeditor/presentation/Bracketed.js");
$require("org/mathdox/formulaeditor/presentation/Node.js");
$require("org/mathdox/formulaeditor/presentation/Row.js");

$require("org/mathdox/formulaeditor/semantics/Integer.js");

$main(function(){

  /**
   * Representation of a column of mathematical expressions in the presentation
   * tree.
   */
  org.mathdox.formulaeditor.presentation.Root =
    $extend(org.mathdox.formulaeditor.presentation.Bracketed, {
      // base of the root (especially if not 2)
      base : null,

      // width of the line
      lineWidth : 1.0,

      // margin between the line and the row
      margin : 2.0,

      // should we draw boxes ?
      drawBox : false,

      drawBaseQ: function() {
        var baseSemantics = this.base.getSemantics();

        return (!baseSemantics || !baseSemantics.value || 
          !baseSemantics.value.value || (baseSemantics.value.value != 2));
      },

      /**
       * Draws the root to the canvas.
       *
       * See also: org.mathdox.formulaeditor.presentation.Node.draw
       */
      draw : function(canvas, x, y, invisible) {
        var middleheight;
        var rootheight;
        var baseheight;
        var height;
        var vlheight;
        var drawBase;

        // invisible drawing of array to set dimensions
        
        this.middle.draw(canvas, 0, 0, true);

        middleheight = this.middle.dimensions.height + this.lineWidth + 
          this.margin*2;

        drawBase = this.drawBaseQ();

        if (drawBase) {
          this.base.draw(canvas, 0, 0, true);
          baseheight = this.base.dimensions.height;
          vlheight = canvas.drawSymbol("vl", 0, 0, true, null).height;
        }

        // if the left and right symbols are brackets set the height
        // XXX check if they are brackets
        if (drawBase) {
          this.leftBracket.minimumHeight = Math.max(middleheight, 
            Math.min(2*baseheight+3*this.margin,
              baseheight+vlheight+3*this.margin ));
        } else {
          this.leftBracket.minimumHeight = middleheight;
        }

        // invisible drawing of brackets to set dimensions
        this.leftBracket.draw(canvas, 0, 0, true);

        rootheight = this.leftBracket.dimensions.height;

        height = rootheight;

        var yAdjust = 0;
        var yAdjustBrackets = 0;
        
        // bracket is higher than the array
        if (height>middleheight) {
          yAdjust = (height - middleheight)/2;
        }

        // baseXAdjust: negative number or 0 indicating how much the base sticks
        // out to the left
        var baseXAdjust = 0;
        if (drawBase) {
          baseXAdjust = Math.min(0, 
            this.leftBracket.dimensions.width/2 - this.base.dimensions.width);
        }
 
        this.dimensions = { 
          height : height,
          width : 
            this.leftBracket.dimensions.width +
            this.middle.dimensions.width - baseXAdjust + this.margin,
          left : x,
          top : y - this.leftBracket.dimensions.height + yAdjust/2 
        };
     
        if (drawBase) {
          this.base.draw(canvas,
            x - this.base.dimensions.left,
            y + yAdjust/2 - Math.min(rootheight/2, vlheight) - 
              (this.base.dimensions.top + this.base.dimensions.height) - 
              2*this.margin,
            invisible);
        }

        this.leftBracket.draw(canvas, 
          x - this.leftBracket.dimensions.left - baseXAdjust, 
          y - (this.leftBracket.dimensions.top +
            this.leftBracket.dimensions.height) + yAdjust/2 , 
          invisible);
        /* XXX adjust vertically */
        this.middle.draw(canvas, 
          x - baseXAdjust + this.leftBracket.dimensions.width -
          this.middle.dimensions.left + this.margin , 
          y - (this.middle.dimensions.top+this.middle.dimensions.height) - 
	  this.margin, invisible);

        if (!invisible) {
          // draw line
          var context = canvas.getContext();

          context.save();
          context.lineWidth = this.lineWidth;
          context.beginPath();
          context.moveTo(x-baseXAdjust+this.leftBracket.dimensions.width - 1,
            this.dimensions.top + this.lineWidth);
          context.lineTo(x+this.dimensions.width, 
            this.dimensions.top + this.lineWidth);
          context.stroke();
          context.closePath();
          context.restore();
        }

        /* XXX adjust */
        if ((!invisible) &&this.drawBox) {
          if (drawBase) {
            canvas.drawBox(this.base.dimensions);
          }
          canvas.drawBox(this.middle.dimensions);
          canvas.drawBox(this.leftBracket.dimensions);
          canvas.drawBoxWithBaseline(this.dimensions,y);
        }

        return this.dimensions;
      },

      getCursorPosition : function(x,y) {
        var dimensions;

        // check for base
        if (this.drawBaseQ()) {
          dimensions = this.base.dimensions;
          if (x < dimensions.left + dimensions.width) {
            return this.base.getCursorPosition(x,y);
          }
        } 

        // check for middle
        dimensions = this.middle.dimensions;
        if (! this.drawBaseQ()) {
          if (x < dimensions.left) {
            return { row: this.parent, index: this.index };
          }
        }
        if (x < dimensions.left + dimensions.width) {
          return this.middle.getCursorPosition(x,y);
        }
        return { row: this.parent, index: this.index };
      },

      getFollowingCursorPosition : function(index, descend) {

        // default value for descend
        if (descend === null || descend === undefined) {
          descend = true;
        }

        // when index is not specified, return the first position in the array
        if (index === null || index === undefined) {
          if (this.drawBaseQ()) {
            return this.base.getFollowingCursorPosition();
          } else {
            return this.middle.getFollowingCursorPosition();
          }
        }
        
        var result = null;

        if (index === 0) {
          if (descend) {
            if (this.drawBaseQ()) {
              result = this.base.getFollowingCursorPosition();
            } else {
              return this.middle.getFollowingCursorPosition();
            }
          }
          if (result === null) {
            result = this.middle.getFollowingCursorPosition();
          }
        }

        if (result === null) {
          // when we're at the end of the matrix, ask the parent of the matrix
          // for the position following this matrix
          if (this.parent !== null) {
            return this.parent.getFollowingCursorPosition(this.index, false);
          }
        }
        
        return result;
      },
      getPrecedingCursorPosition : function(index, descend) {

        // default value for descend
        if (descend === null || descend === undefined) {
          descend = true;
        }

        // when index is not specified, return the first position in the array
        if (index === null || index === undefined) {
          return this.middle.getPrecedingCursorPosition();
        }
        
        var result = null;

        if (index == 1) {
          if (descend) {
            result = this.middle.getPrecedingCursorPosition();
          }
          if (result === null) {
            if (this.drawBaseQ()) {
              result = this.base.getPrecedingCursorPosition();
            }
          }
        }

        if (result === null) {
          // when we're at the beginning of the matrix, ask the parent of the
          // matrix for the position before this matrix
          if (this.parent !== null) {
            return { row: this.parent, index: this.index };
          }
        }
        
        return result;
      },
      initialize : function () {
        if (arguments.length>0) {
          this.leftBracket = 
            new org.mathdox.formulaeditor.presentation.Bracket("v");
          this.middle = arguments[0];
          this.base = arguments[1];
          this.children = [];
          this.children.push(this.base);
          this.children.push(this.middle);
        } else {
          this.children = [];
        }

        var presentation = org.mathdox.formulaeditor.presentation;
        /* copy the cursor/position functions from Row */

        var row = new presentation.Row(); // only an instance has the functions

        for (var i=this.functionsFromRow.length - 1; i>=0; i--) {
          if (! this[this.functionsFromRow[i]] ) {
            this[this.functionsFromRow[i]] = 
              row[ this.functionsFromRow[i] ];
          }
        }
        this.updateChildren();
      },

      getSemantics : function() {
        var root;

        var presentation = org.mathdox.formulaeditor.semantics;
        root = new presentation.Arith1Root(this.middle.getSemantics().value, 
          this.base.getSemantics().value);
        return {
          value : root,
          rule  : "braces"
        };
      }


    });

});
