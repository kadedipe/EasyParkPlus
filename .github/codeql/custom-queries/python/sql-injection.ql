/**
 * @name SQL injection detection
 * @description Detects potential SQL injection vulnerabilities
 * @kind problem
 * @id py/sql-injection-custom
 * @tags security
 * @severity error
 */

import python
import semmle.python.security.strings.Basic
import semmle.python.security.strings.Untrusted

from DataFlow::Node source, DataFlow::Node sink, string description
where
  source instanceof UntrustedStringSource and
  sink instanceof SQLConstruction and
  DataFlow::flow(source, sink)
select sink, description, source, "This SQL query might be vulnerable to injection."