/**
 * Sidecar JavaScript Interceptor
 * Runs in the page's main world to hook dangerous JavaScript functions.
 * Implements PRD section 3.1.4.
 * 
 * This script is injected via content-script.js and runs in the page context,
 * not the extension's isolated world.
 */

(function() {
  'use strict';

  console.log('[Sidecar Interceptor] Initializing function hooks...');

  /**
   * Send intercepted call data back to content script via postMessage
   */
  function reportExecution(functionName, inputValue, context = {}) {
    try {
      console.log(`[Sidecar Interceptor] Intercepted call to '${functionName}' with value:`, inputValue);
      const stackTrace = new Error().stack;
      
      window.postMessage({
        type: 'SIDECAR_JS_EXECUTION',
        detail: {
          functionName: functionName,
          inputValue: String(inputValue).substring(0, 1000), // Limit size
          stackTrace: stackTrace,
          context: context,
          timestamp: new Date().toISOString()
        }
      }, '*');
    } catch (error) {
      console.error('[Sidecar Interceptor] Error reporting execution:', error);
    }
  }

  /**
   * Hook innerHTML setter
   * One of the most common XSS sinks
   */
  try {
    const originalInnerHTMLDescriptor = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML');
    if (originalInnerHTMLDescriptor && originalInnerHTMLDescriptor.set) {
      const originalInnerHTMLSetter = originalInnerHTMLDescriptor.set;

      Object.defineProperty(Element.prototype, 'innerHTML', {
        set: function(value) {
          reportExecution('innerHTML', value, {
            tagName: this.tagName,
            id: this.id,
            className: this.className
          });
          return originalInnerHTMLSetter.call(this, value);
        },
        get: originalInnerHTMLDescriptor.get,
        configurable: true,
        enumerable: true
      });

      console.log('[Sidecar Interceptor] ✓ innerHTML hook installed');
    }
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook innerHTML:', error);
  }

  /**
   * Hook outerHTML setter
   */
  try {
    const originalOuterHTMLDescriptor = Object.getOwnPropertyDescriptor(Element.prototype, 'outerHTML');
    if (originalOuterHTMLDescriptor && originalOuterHTMLDescriptor.set) {
      const originalOuterHTMLSetter = originalOuterHTMLDescriptor.set;

      Object.defineProperty(Element.prototype, 'outerHTML', {
        set: function(value) {
          reportExecution('outerHTML', value, {
            tagName: this.tagName,
            id: this.id,
            className: this.className
          });
          return originalOuterHTMLSetter.call(this, value);
        },
        get: originalOuterHTMLDescriptor.get,
        configurable: true,
        enumerable: true
      });

      console.log('[Sidecar Interceptor] ✓ outerHTML hook installed');
    }
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook outerHTML:', error);
  }

  /**
   * Hook eval
   * Dangerous function that executes strings as code
   */
  try {
    const originalEval = window.eval;
    
    window.eval = function(code) {
      reportExecution('eval', code);
      return originalEval.call(window, code);
    };

    console.log('[Sidecar Interceptor] ✓ eval hook installed');
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook eval:', error);
  }

  /**
   * Hook document.write
   * Can be used for DOM-based XSS
   */
  try {
    const originalDocumentWrite = document.write;
    
    document.write = function(content) {
      reportExecution('document.write', content);
      return originalDocumentWrite.call(document, content);
    };

    console.log('[Sidecar Interceptor] ✓ document.write hook installed');
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook document.write:', error);
  }

  /**
   * Hook document.writeln
   */
  try {
    const originalDocumentWriteln = document.writeln;
    
    document.writeln = function(content) {
      reportExecution('document.writeln', content);
      return originalDocumentWriteln.call(document, content);
    };

    console.log('[Sidecar Interceptor] ✓ document.writeln hook installed');
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook document.writeln:', error);
  }

  /**
   * Hook addEventListener for 'message' events
   * To detect postMessage handlers (which can be vulnerable)
   */
  try {
    const originalAddEventListener = EventTarget.prototype.addEventListener;
    
    EventTarget.prototype.addEventListener = function(type, listener, options) {
      if (type === 'message') {
        reportExecution('addEventListener', 'message event listener added', {
          target: this.constructor.name,
          listenerString: listener.toString().substring(0, 500)
        });
      }
      return originalAddEventListener.call(this, type, listener, options);
    };

    console.log('[Sidecar Interceptor] ✓ addEventListener (message) hook installed');
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook addEventListener:', error);
  }

  /**
   * Hook postMessage
   * Monitor cross-origin messaging
   */
  try {
    const originalPostMessage = window.postMessage;
    
    window.postMessage = function(message, targetOrigin, transfer) {
      // Don't report our own Sidecar messages
      if (!(message && message.type && message.type.startsWith('SIDECAR_'))) {
        reportExecution('postMessage', JSON.stringify(message).substring(0, 500), {
          targetOrigin: targetOrigin
        });
      }
      return originalPostMessage.call(window, message, targetOrigin, transfer);
    };

    console.log('[Sidecar Interceptor] ✓ postMessage hook installed');
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook postMessage:', error);
  }

  /**
   * Hook Function constructor
   * Can be used to create functions from strings (like eval)
   */
  try {
    const OriginalFunction = Function;
    
    window.Function = function(...args) {
      const code = args.length > 0 ? args[args.length - 1] : '';
      reportExecution('Function constructor', code);
      return new OriginalFunction(...args);
    };
    
    // Preserve prototype
    window.Function.prototype = OriginalFunction.prototype;

    console.log('[Sidecar Interceptor] ✓ Function constructor hook installed');
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook Function constructor:', error);
  }

  /**
   * Hook setTimeout with string argument
   * String arguments are eval'd
   */
  try {
    const originalSetTimeout = window.setTimeout;
    
    window.setTimeout = function(handler, timeout, ...args) {
      if (typeof handler === 'string') {
        reportExecution('setTimeout', handler, {
          timeout: timeout
        });
      }
      return originalSetTimeout.call(window, handler, timeout, ...args);
    };

    console.log('[Sidecar Interceptor] ✓ setTimeout hook installed');
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook setTimeout:', error);
  }

  /**
   * Hook setInterval with string argument
   */
  try {
    const originalSetInterval = window.setInterval;
    
    window.setInterval = function(handler, timeout, ...args) {
      if (typeof handler === 'string') {
        reportExecution('setInterval', handler, {
          timeout: timeout
        });
      }
      return originalSetInterval.call(window, handler, timeout, ...args);
    };

    console.log('[Sidecar Interceptor] ✓ setInterval hook installed');
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook setInterval:', error);
  }

  /**
   * Hook insertAdjacentHTML
   * Another DOM manipulation sink
   */
  try {
    const originalInsertAdjacentHTML = Element.prototype.insertAdjacentHTML;
    
    Element.prototype.insertAdjacentHTML = function(position, html) {
      reportExecution('insertAdjacentHTML', html, {
        position: position,
        tagName: this.tagName,
        id: this.id
      });
      return originalInsertAdjacentHTML.call(this, position, html);
    };

    console.log('[Sidecar Interceptor] ✓ insertAdjacentHTML hook installed');
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook insertAdjacentHTML:', error);
  }

  /**
   * Hook location setters
   * Can be used for open redirects
   */
  try {
    const originalLocationDescriptor = Object.getOwnPropertyDescriptor(window, 'location');
    const originalLocation = window.location;

    // Hook location.href setter
    const originalHrefDescriptor = Object.getOwnPropertyDescriptor(Location.prototype, 'href');
    if (originalHrefDescriptor && originalHrefDescriptor.set) {
      const originalHrefSetter = originalHrefDescriptor.set;

      Object.defineProperty(Location.prototype, 'href', {
        set: function(value) {
          reportExecution('location.href', value, {
            currentHref: window.location.href
          });
          return originalHrefSetter.call(this, value);
        },
        get: originalHrefDescriptor.get,
        configurable: true,
        enumerable: true
      });

      console.log('[Sidecar Interceptor] ✓ location.href hook installed');
    }
  } catch (error) {
    console.error('[Sidecar Interceptor] Failed to hook location.href:', error);
  }

  console.log('[Sidecar Interceptor] All hooks installed successfully!');

})();
