/**
 * @name XSS detection
 * @description Detects potential Cross-Site Scripting vulnerabilities
 * @kind problem
 * @id js/xss-custom
 * @tags security
 * @severity error
 */

import javascript

from DataFlow::SourceNode source, DataFlow::Node sink
where
  source instanceof RemoteFlowSource and
  sink instanceof HtmlInjectionSink and
  DataFlow::flow(source, sink)
select sink, "Potential XSS vulnerability from $@.", source, "user input"