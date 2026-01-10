#!/usr/bin/env python3
"""
Integration Test Runner for Parking Management System

This script runs integration tests with various configurations and
generates comprehensive reports.
"""

import unittest
import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

def run_all_integration_tests(output_dir=None, verbosity=2):
    """Run all integration tests"""
    from tests.integration.test_integration import run_integration_tests
    from tests.integration.test_critical_scenarios import run_critical_tests
    
    print("=" * 70)
    print("PARKING MANAGEMENT SYSTEM - INTEGRATION TEST SUITE")
    print("=" * 70)
    
    results = {}
    
    # Run critical tests first
    print("\n" + "=" * 70)
    print("PHASE 1: CRITICAL SCENARIO TESTS")
    print("=" * 70)
    critical_result = run_critical_tests()
    results["critical"] = {
        "tests_run": critical_result.testsRun,
        "failures": len(critical_result.failures),
        "errors": len(critical_result.errors),
        "skipped": len(critical_result.skipped),
        "successful": critical_result.wasSuccessful()
    }
    
    # Run comprehensive integration tests
    print("\n" + "=" * 70)
    print("PHASE 2: COMPREHENSIVE INTEGRATION TESTS")
    print("=" * 70)
    integration_result = run_integration_tests()
    results["integration"] = {
        "tests_run": integration_result.testsRun,
        "failures": len(integration_result.failures),
        "errors": len(integration_result.errors),
        "skipped": len(integration_result.skipped),
        "successful": integration_result.wasSuccessful()
    }
    
    # Generate report
    if output_dir:
        generate_report(results, output_dir)
    
    # Overall result
    print("\n" + "=" * 70)
    print("OVERALL INTEGRATION TEST RESULTS")
    print("=" * 70)
    
    total_tests = results["critical"]["tests_run"] + results["integration"]["tests_run"]
    total_failures = results["critical"]["failures"] + results["integration"]["failures"]
    total_errors = results["critical"]["errors"] + results["integration"]["errors"]
    
    print(f"\nTotal Tests Run: {total_tests}")
    print(f"Total Failures: {total_failures}")
    print(f"Total Errors: {total_errors}")
    print(f"Total Skipped: {results['integration']['skipped']}")
    
    all_successful = (results["critical"]["successful"] and 
                      results["integration"]["successful"])
    
    if all_successful:
        print("\n✅ ALL INTEGRATION TESTS PASSED!")
        print("System components are working together correctly.")
        return True
    else:
        print("\n❌ SOME INTEGRATION TESTS FAILED!")
        print("Review the test output above for details.")
        return False

def generate_report(results, output_dir):
    """Generate integration test report"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # JSON report
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "summary": {
            "total_tests": results["critical"]["tests_run"] + results["integration"]["tests_run"],
            "total_failures": results["critical"]["failures"] + results["integration"]["failures"],
            "total_errors": results["critical"]["errors"] + results["integration"]["errors"],
            "all_passed": (results["critical"]["successful"] and 
                          results["integration"]["successful"])
        }
    }
    
    json_path = output_path / "integration_test_report.json"
    with open(json_path, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    # HTML report
    html_report = generate_html_report(report_data)
    html_path = output_path / "integration_test_report.html"
    with open(html_path, 'w') as f:
        f.write(html_report)
    
    print(f"\nReports generated in: {output_path}")
    print(f"  • {json_path.name}")
    print(f"  • {html_path.name}")

def generate_html_report(report_data):
    """Generate HTML report"""
    timestamp = datetime.fromisoformat(report_data["timestamp"])
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Integration Test Report - Parking Management System</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .section {{
            background-color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .success {{
            color: #27ae60;
            font-weight: bold;
        }}
        .failure {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .warning {{
            color: #f39c12;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        .summary-box {{
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
        }}
        .summary-item {{
            text-align: center;
            padding: 20px;
            border-radius: 5px;
            background-color: #ecf0f1;
            flex: 1;
            margin: 0 10px;
        }}
        .summary-number {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Parking Management System</h1>
        <h2>Integration Test Report</h2>
        <p>Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="section">
        <h2>Test Summary</h2>
        <div class="summary-box">
            <div class="summary-item">
                <div class="summary-number">{report_data["summary"]["total_tests"]}</div>
                <div>Total Tests</div>
            </div>
            <div class="summary-item">
                <div class="summary-number" class="{ 'failure' if report_data['summary']['total_failures'] > 0 else 'success' }">
                    {report_data["summary"]["total_failures"]}
                </div>
                <div>Failures</div>
            </div>
            <div class="summary-item">
                <div class="summary-number" class="{ 'failure' if report_data['summary']['total_errors'] > 0 else 'success' }">
                    {report_data["summary"]["total_errors"]}
                </div>
                <div>Errors</div>
            </div>
            <div class="summary-item">
                <div class="summary-number" class="{ 'success' if report_data['summary']['all_passed'] else 'failure' }">
                    {'PASS' if report_data['summary']['all_passed'] else 'FAIL'}
                </div>
                <div>Overall Result</div>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>Detailed Results</h2>
        
        <h3>Critical Scenario Tests</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>Tests Run</td>
                <td>{report_data["results"]["critical"]["tests_run"]}</td>
                <td>-</td>
            </tr>
            <tr>
                <td>Failures</td>
                <td>{report_data["results"]["critical"]["failures"]}</td>
                <td class="{ 'failure' if report_data['results']['critical']['failures'] > 0 else 'success' }">
                    {'❌' if report_data['results']['critical']['failures'] > 0 else '✅'}
                </td>
            </tr>
            <tr>
                <td>Errors</td>
                <td>{report_data["results"]["critical"]["errors"]}</td>
                <td class="{ 'failure' if report_data['results']['critical']['errors'] > 0 else 'success' }">
                    {'❌' if report_data['results']['critical']['errors'] > 0 else '✅'}
                </td>
            </tr>
            <tr>
                <td>Overall Result</td>
                <td colspan="2" class="{ 'success' if report_data['results']['critical']['successful'] else 'failure' }">
                    {'✅ PASSED' if report_data['results']['critical']['successful'] else '❌ FAILED'}
                </td>
            </tr>
        </table>
        
        <h3>Comprehensive Integration Tests</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>Tests Run</td>
                <td>{report_data["results"]["integration"]["tests_run"]}</td>
                <td>-</td>
            </tr>
            <tr>
                <td>Failures</td>
                <td>{report_data["results"]["integration"]["failures"]}</td>
                <td class="{ 'failure' if report_data['results']['integration']['failures'] > 0 else 'success' }">
                    {'❌' if report_data['results']['integration']['failures'] > 0 else '✅'}
                </td>
            </tr>
            <tr>
                <td>Errors</td>
                <td>{report_data["results"]["integration"]["errors"]}</td>
                <td class="{ 'failure' if report_data['results']['integration']['errors'] > 0 else 'success' }">
                    {'❌' if report_data['results']['integration']['errors'] > 0 else '✅'}
                </td>
            </tr>
            <tr>
                <td>Skipped</td>
                <td>{report_data["results"]["integration"]["skipped"]}</td>
                <td class="warning">⚠</td>
            </tr>
            <tr>
                <td>Overall Result</td>
                <td colspan="2" class="{ 'success' if report_data['results']['integration']['successful'] else 'failure' }">
                    {'✅ PASSED' if report_data['results']['integration']['successful'] else '❌ FAILED'}
                </td>
            </tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Test Categories</h2>
        <p>The integration tests cover the following areas:</p>
        <ul>
            <li><strong>GUI + Controller Integration:</strong> Tests interaction between user interface and business logic</li>
            <li><strong>View + Controller Integration:</strong> Tests data flow between views and controllers</li>
            <li><strong>Dialog + Controller Integration:</strong> Tests form handling and validation</li>
            <li><strong>Service Layer Integration:</strong> Tests business service interactions</li>
            <li><strong>Command Processor Integration:</strong> Tests command pattern implementation</li>
            <li><strong>End-to-End Scenarios:</strong> Tests complete user workflows</li>
            <li><strong>Data Flow Integration:</strong> Tests data passing between components</li>
            <li><strong>Event Handling:</strong> Tests user interaction handling</li>
            <li><strong>Concurrent Operations:</strong> Tests multi-threaded scenarios</li>
            <li><strong>Error Recovery:</strong> Tests system resilience</li>
            <li><strong>Performance:</strong> Tests system responsiveness</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        """
    
    if report_data["summary"]["all_passed"]:
        html += """
        <p class="success">✅ All integration tests passed successfully!</p>
        <p>The system components are working together correctly. The system is ready for:</p>
        <ul>
            <li>User acceptance testing</li>
            <li>Deployment to staging environment</li>
            <li>Performance and load testing</li>
        </ul>
        """
    else:
        html += f"""
        <p class="failure">❌ Some integration tests failed.</p>
        <p>Review the following areas:</p>
        <ul>
            <li>Critical failures: {report_data['results']['critical']['failures']} failures need immediate attention</li>
            <li>Integration errors: {report_data['results']['integration']['errors']} errors in component interaction</li>
            <li>Skipped tests: {report_data['results']['integration']['skipped']} tests were skipped (may need dependencies)</li>
        </ul>
        <p><strong>Next steps:</strong></p>
        <ol>
            <li>Fix critical test failures first</li>
            <li>Address integration errors</li>
            <li>Review skipped tests and add required dependencies</li>
            <li>Re-run the integration test suite</li>
        </ol>
        """
    
    html += """
    </div>
    
    <div class="section">
        <p><em>Report generated by Integration Test Runner</em></p>
        <p><em>Parking Management System v1.0.0</em></p>
    </div>
</body>
</html>
"""
    
    return html

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Run integration tests for Parking Management System'
    )
    
    parser.add_argument('--output-dir', '-o', 
                       default='./test_reports/integration',
                       help='Output directory for test reports')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--critical-only', action='store_true',
                       help='Run only critical scenario tests')
    parser.add_argument('--no-report', action='store_true',
                       help='Do not generate HTML/JSON reports')
    
    args = parser.parse_args()
    
    verbosity = 2 if args.verbose else 1
    
    if args.critical_only:
        # Just run critical tests
        from tests.integration.test_critical_scenarios import run_critical_tests
        result = run_critical_tests()
        success = result.wasSuccessful()
    else:
        # Run all integration tests
        output_dir = None if args.no_report else args.output_dir
        success = run_all_integration_tests(output_dir, verbosity)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()