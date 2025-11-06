#!/usr/bin/env python3
"""
Test script for Correlation Timeline UI

This script verifies that:
1. The frontend serves the timeline UI files correctly
2. The API endpoints return proper data
3. JavaScript files have no syntax errors
4. CSS files are properly formatted
"""

import requests
import json
import re
from pathlib import Path


class TimelineUITester:
    def __init__(self):
        self.frontend_url = "http://localhost:9999"
        self.api_url = "http://localhost:8000"
        self.results = []
        
    def log(self, test_name, status, details=""):
        """Log test result"""
        symbol = "✅" if status else "❌"
        self.results.append({
            "test": test_name,
            "status": status,
            "details": details
        })
        print(f"{symbol} {test_name}")
        if details:
            print(f"   {details}")
    
    def test_frontend_accessibility(self):
        """Test 1: Frontend is accessible"""
        try:
            response = requests.get(self.frontend_url, timeout=5)
            self.log(
                "Frontend Accessibility",
                response.status_code == 200,
                f"Status: {response.status_code}"
            )
            return response.status_code == 200
        except Exception as e:
            self.log("Frontend Accessibility", False, str(e))
            return False
    
    def test_html_contains_timeline_tab(self):
        """Test 2: HTML contains timeline tab structure"""
        try:
            response = requests.get(self.frontend_url, timeout=5)
            html = response.text
            
            has_tab_button = 'data-tab="correlation-timeline"' in html
            has_tab_content = 'id="correlation-timeline-tab"' in html
            has_script = 'correlation-timeline.js' in html
            
            all_present = has_tab_button and has_tab_content and has_script
            
            details = []
            if not has_tab_button:
                details.append("Missing tab button")
            if not has_tab_content:
                details.append("Missing tab content")
            if not has_script:
                details.append("Missing script tag")
            
            self.log(
                "HTML Timeline Structure",
                all_present,
                " | ".join(details) if details else "All elements present"
            )
            return all_present
        except Exception as e:
            self.log("HTML Timeline Structure", False, str(e))
            return False
    
    def test_javascript_file_accessible(self):
        """Test 3: correlation-timeline.js is accessible"""
        try:
            response = requests.get(
                f"{self.frontend_url}/correlation-timeline.js",
                timeout=5
            )
            
            is_accessible = response.status_code == 200
            has_content = len(response.text) > 0
            is_js = 'function' in response.text or 'const' in response.text
            
            all_good = is_accessible and has_content and is_js
            
            self.log(
                "JavaScript File Accessible",
                all_good,
                f"Size: {len(response.text)} bytes, Contains JS: {is_js}"
            )
            return all_good
        except Exception as e:
            self.log("JavaScript File Accessible", False, str(e))
            return False
    
    def test_javascript_functions_present(self):
        """Test 4: Required JavaScript functions exist"""
        try:
            response = requests.get(
                f"{self.frontend_url}/correlation-timeline.js",
                timeout=5
            )
            js_content = response.text
            
            required_functions = [
                'initCorrelationTimeline',
                'loadTimelineData',
                'loadTimelineStats',
                'renderTimeline',
                'renderTimelineEntry',
                'toggleTimelineEntry'
            ]
            
            missing = []
            for func in required_functions:
                if func not in js_content:
                    missing.append(func)
            
            all_present = len(missing) == 0
            
            self.log(
                "JavaScript Functions Present",
                all_present,
                f"Missing: {', '.join(missing)}" if missing else "All functions present"
            )
            return all_present
        except Exception as e:
            self.log("JavaScript Functions Present", False, str(e))
            return False
    
    def test_css_timeline_styles(self):
        """Test 5: CSS contains timeline styles"""
        try:
            response = requests.get(f"{self.frontend_url}/styles.css", timeout=5)
            css_content = response.text
            
            required_classes = [
                '.timeline-entry',
                '.timeline-entry-header',
                '.timeline-entry-content',
                '.correlated-events',
                '.event-item',
                '#timeline-stats',
                '#timeline-container'
            ]
            
            missing = []
            for css_class in required_classes:
                if css_class not in css_content:
                    missing.append(css_class)
            
            all_present = len(missing) == 0
            
            self.log(
                "CSS Timeline Styles",
                all_present,
                f"Missing: {', '.join(missing)}" if missing else "All styles present"
            )
            return all_present
        except Exception as e:
            self.log("CSS Timeline Styles", False, str(e))
            return False
    
    def test_api_stats_endpoint(self):
        """Test 6: /api/correlation-stats endpoint works"""
        try:
            response = requests.get(
                f"{self.api_url}/api/correlation-stats",
                timeout=5
            )
            
            if response.status_code != 200:
                self.log("API Stats Endpoint", False, f"Status: {response.status_code}")
                return False
            
            data = response.json()
            
            has_http_records = 'http_records' in data
            has_enrichment = 'enrichment_events' in data
            has_metrics = 'correlation_metrics' in data
            
            all_present = has_http_records and has_enrichment and has_metrics
            
            details = f"HTTP Records: {data.get('http_records', {}).get('total', 0)}, "
            details += f"Events: {data.get('enrichment_events', {}).get('total', 0)}"
            
            self.log("API Stats Endpoint", all_present, details)
            return all_present
        except Exception as e:
            self.log("API Stats Endpoint", False, str(e))
            return False
    
    def test_api_timeline_endpoint(self):
        """Test 7: /api/correlation-timeline endpoint works"""
        try:
            response = requests.get(
                f"{self.api_url}/api/correlation-timeline?page=1&page_size=5",
                timeout=5
            )
            
            if response.status_code != 200:
                self.log("API Timeline Endpoint", False, f"Status: {response.status_code}")
                return False
            
            data = response.json()
            
            has_timeline = 'timeline' in data
            has_pagination = 'pagination' in data
            has_summary = 'summary' in data
            
            all_present = has_timeline and has_pagination and has_summary
            
            timeline_count = len(data.get('timeline', []))
            total = data.get('pagination', {}).get('total_records', 0)
            
            details = f"Timeline entries: {timeline_count}, Total records: {total}"
            
            self.log("API Timeline Endpoint", all_present, details)
            return all_present
        except Exception as e:
            self.log("API Timeline Endpoint", False, str(e))
            return False
    
    def test_api_timeline_structure(self):
        """Test 8: Timeline API returns proper data structure"""
        try:
            response = requests.get(
                f"{self.api_url}/api/correlation-timeline?page=1&page_size=1",
                timeout=5
            )
            
            data = response.json()
            timeline = data.get('timeline', [])
            
            if len(timeline) == 0:
                self.log("API Timeline Structure", True, "No records (database empty)")
                return True
            
            entry = timeline[0]
            
            has_http_record = 'http_record' in entry
            has_corr_events = 'correlated_events' in entry
            has_window = 'correlation_window' in entry
            has_stats = 'statistics' in entry
            
            all_present = has_http_record and has_corr_events and has_window and has_stats
            
            http_record = entry.get('http_record', {})
            has_method = 'method' in http_record
            has_url = 'url' in http_record
            has_status = 'status' in http_record
            
            structure_valid = all_present and has_method and has_url and has_status
            
            self.log(
                "API Timeline Structure",
                structure_valid,
                "All required fields present" if structure_valid else "Missing fields"
            )
            return structure_valid
        except Exception as e:
            self.log("API Timeline Structure", False, str(e))
            return False
    
    def test_api_cors_enabled(self):
        """Test 9: CORS is enabled for frontend"""
        try:
            response = requests.options(
                f"{self.api_url}/api/correlation-stats",
                headers={"Origin": self.frontend_url},
                timeout=5
            )
            
            cors_header = response.headers.get('Access-Control-Allow-Origin', '')
            cors_enabled = cors_header == '*' or self.frontend_url in cors_header
            
            self.log(
                "API CORS Enabled",
                cors_enabled,
                f"CORS header: {cors_header if cors_header else 'Not set'}"
            )
            return cors_enabled
        except Exception as e:
            self.log("API CORS Enabled", False, str(e))
            return False
    
    def test_javascript_no_syntax_errors(self):
        """Test 10: JavaScript has no obvious syntax errors"""
        try:
            response = requests.get(
                f"{self.frontend_url}/correlation-timeline.js",
                timeout=5
            )
            js_content = response.text
            
            # Check for common syntax errors
            errors = []
            
            # Check bracket/brace matching
            if js_content.count('{') != js_content.count('}'):
                errors.append("Mismatched curly braces")
            
            if js_content.count('(') != js_content.count(')'):
                errors.append("Mismatched parentheses")
            
            if js_content.count('[') != js_content.count(']'):
                errors.append("Mismatched brackets")
            
            # Check for incomplete function definitions
            if 'function' in js_content:
                functions = re.findall(r'function\s+\w+\s*\([^)]*\)\s*{', js_content)
                if len(functions) == 0 and 'function' in js_content:
                    errors.append("Malformed function definitions")
            
            no_errors = len(errors) == 0
            
            self.log(
                "JavaScript Syntax Check",
                no_errors,
                " | ".join(errors) if errors else "No syntax errors detected"
            )
            return no_errors
        except Exception as e:
            self.log("JavaScript Syntax Check", False, str(e))
            return False
    
    def run_all_tests(self):
        """Run all tests and print summary"""
        print("\n" + "="*60)
        print("CORRELATION TIMELINE UI TEST SUITE")
        print("="*60 + "\n")
        
        tests = [
            self.test_frontend_accessibility,
            self.test_html_contains_timeline_tab,
            self.test_javascript_file_accessible,
            self.test_javascript_functions_present,
            self.test_css_timeline_styles,
            self.test_api_stats_endpoint,
            self.test_api_timeline_endpoint,
            self.test_api_timeline_structure,
            self.test_api_cors_enabled,
            self.test_javascript_no_syntax_errors
        ]
        
        for test in tests:
            test()
            print()
        
        # Print summary
        passed = sum(1 for r in self.results if r['status'])
        total = len(self.results)
        
        print("="*60)
        print(f"SUMMARY: {passed}/{total} tests passed")
        print("="*60)
        
        if passed == total:
            print("✅ All tests passed! Timeline UI is ready.")
        else:
            print("❌ Some tests failed. Review the results above.")
        
        return passed == total


if __name__ == "__main__":
    tester = TimelineUITester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
