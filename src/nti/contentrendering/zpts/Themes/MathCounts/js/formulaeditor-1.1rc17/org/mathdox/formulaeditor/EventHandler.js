$package("org.mathdox.formulaeditor");

$identify("org/mathdox/formulaeditor/EventHandler.js");

$main(function(){

  org.mathdox.formulaeditor.EventHandler = $extend(Object, {

    initialize : function() {

      // save the 'this' pointer so that it can be used in the event handlers
      var handler = this;

      // register the onkeydown handler, if present
      if (this.onkeydown instanceof Function) {

        var saved1 = window.onkeydown;
        document.onkeydown = function(event) {

          if (!event) {
            event = window.event; // MSIE's non-standard way of supplying events
          }

          return handler.onkeydown(event) && saved1 && saved1(event);

        };

      }

      // register the onkeypress handler, if present
      if (this.onkeypress instanceof Function) {

        var saved2 = window.onkeypress;
        document.onkeypress = function(event) {

          if (!event) {
            event = window.event; // MSIE's non-standard way of supplying events
          }

          if (!("charCode" in event)) {
            event.charCode = event.keyCode; // MSIE doesn't set charCode
          }

          return handler.onkeypress(event) && saved2 && saved2(event);

        };

      }

      // register the onmousedown handler, if present
      if (this.onmousedown instanceof Function) {

        var saved3 = window.onclick;
        document.onmousedown = function(event) {

          if (!event) {
            event = window.event; // MSIE's non-standard way of supplying events
          }

          return handler.onmousedown(event) && saved3 && saved3(event);

        };

      }

    }

  });

});
