"""
Data Quality Migration for Vehicle Data
Validates and reports on vehicle data quality in Elasticsearch
"""

import logging
from datetime import datetime
from elasticsearch import Elasticsearch, NotFoundError
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VehicleDataQualityMigration:
    """
    Migration to check and report on vehicle data quality in Elasticsearch
    """
    
    def __init__(self, es_host='localhost', es_port=9200, auth=None, index_pattern='vehicles-*'):
        """
        Initialize the migration
        
        Args:
            es_host: Elasticsearch host
            es_port: Elasticsearch port
            auth: Authentication tuple (username, password) or None
            index_pattern: Index pattern to search
        """
        self.es_host = es_host
        self.es_port = es_port
        self.auth = auth
        self.index_pattern = index_pattern
        
        # Build connection URL
        self.es_url = f"http://{es_host}:{es_port}"
        
        # Initialize Elasticsearch client
        if auth:
            self.es_client = Elasticsearch(
                [self.es_url],
                http_auth=auth,
                timeout=30
            )
        else:
            self.es_client = Elasticsearch([self.es_url], timeout=30)
        
        self.results = {}
    
    def run_query(self, query_body):
        """
        Run a search query and return results
        
        Args:
            query_body: Query body dictionary
            
        Returns:
            Search response
        """
        try:
            response = self.es_client.search(
                index=self.index_pattern,
                body=query_body,
                track_total_hits=True,
                size=0
            )
            return response
        except NotFoundError:
            logger.warning(f"No indices found matching pattern: {self.index_pattern}")
            return {'hits': {'total': {'value': 0}}}
        except Exception as e:
            logger.error(f"Error running query: {str(e)}")
            raise
    
    def get_total_count(self):
        """Get total number of vehicles"""
        query = {"track_total_hits": True}
        response = self.run_query(query)
        return response['hits']['total']['value']
    
    def get_missing_field_count(self, field_name):
        """
        Get count of documents missing a specific field
        
        Args:
            field_name: Name of the field to check
            
        Returns:
            Count of documents missing the field
        """
        query = {
            "query": {
                "bool": {
                    "must_not": {
                        "exists": {
                            "field": field_name
                        }
                    }
                }
            },
            "track_total_hits": True
        }
        response = self.run_query(query)
        return response['hits']['total']['value']
    
    def get_expired_count(self, field_path):
        """
        Get count of documents with expired dates
        
        Args:
            field_path: Path to the date field (e.g., 'registration.expiry_date')
            
        Returns:
            Count of expired documents
        """
        query = {
            "query": {
                "range": {
                    field_path: {
                        "lt": "now"
                    }
                }
            },
            "track_total_hits": True
        }
        response = self.run_query(query)
        return response['hits']['total']['value']
    
    def get_boolean_count(self, field_path, value=True):
        """
        Get count of documents with specific boolean value
        
        Args:
            field_path: Path to the boolean field
            value: Boolean value to match
            
        Returns:
            Count of matching documents
        """
        query = {
            "query": {
                "term": {
                    field_path: value
                }
            },
            "track_total_hits": True
        }
        response = self.run_query(query)
        return response['hits']['total']['value']
    
    def get_field_distribution(self, field_name, size=20):
        """
        Get distribution of values for a field
        
        Args:
            field_name: Name of the field
            size: Number of buckets to return
            
        Returns:
            List of buckets with keys and counts
        """
        query = {
            "aggs": {
                "distribution": {
                    "terms": {
                        "field": field_name,
                        "size": size
                    }
                }
            }
        }
        response = self.run_query(query)
        
        buckets = []
        if 'aggregations' in response and 'distribution' in response['aggregations']:
            buckets = response['aggregations']['distribution']['buckets']
        
        return buckets
    
    def calculate_quality_score(self):
        """Calculate overall data quality score"""
        total = self.results.get('total', 0)
        missing_plate_pct = self.results.get('missing_plate_pct', 0)
        missing_vin_pct = self.results.get('missing_vin_pct', 0)
        
        if total > 0:
            quality_score = 100 - ((missing_plate_pct + missing_vin_pct) / 2)
            return round(quality_score, 2)
        return 0
    
    def get_quality_grade(self, score):
        """Get letter grade based on quality score"""
        if score > 95:
            return 'A'
        elif score > 90:
            return 'B'
        elif score > 80:
            return 'C'
        else:
            return 'D - Improvement needed'
    
    def run_quality_check(self):
        """
        Run all quality checks and compile results
        """
        logger.info("Starting vehicle data quality check")
        
        # Get total count
        total = self.get_total_count()
        self.results['total'] = total
        logger.info(f"Total vehicles: {total}")
        
        if total == 0:
            logger.warning("No vehicles found in indices")
            return self.results
        
        # Check missing fields
        missing_plate = self.get_missing_field_count('license_plate')
        missing_plate_pct = round((missing_plate * 100 / total), 2)
        self.results['missing_plate'] = missing_plate
        self.results['missing_plate_pct'] = missing_plate_pct
        logger.info(f"Missing license plate: {missing_plate} ({missing_plate_pct}%)")
        
        missing_vin = self.get_missing_field_count('vin')
        missing_vin_pct = round((missing_vin * 100 / total), 2)
        self.results['missing_vin'] = missing_vin
        self.results['missing_vin_pct'] = missing_vin_pct
        logger.info(f"Missing VIN: {missing_vin} ({missing_vin_pct}%)")
        
        # Check expired items
        expired_reg = self.get_expired_count('registration.expiry_date')
        expired_reg_pct = round((expired_reg * 100 / total), 2)
        self.results['expired_registration'] = expired_reg
        self.results['expired_registration_pct'] = expired_reg_pct
        logger.info(f"Expired registration: {expired_reg} ({expired_reg_pct}%)")
        
        expired_ins = self.get_expired_count('insurance.expiry_date')
        expired_ins_pct = round((expired_ins * 100 / total), 2)
        self.results['expired_insurance'] = expired_ins
        self.results['expired_insurance_pct'] = expired_ins_pct
        logger.info(f"Expired insurance: {expired_ins} ({expired_ins_pct}%)")
        
        # Check status fields
        blacklisted = self.get_boolean_count('status.is_blacklisted', True)
        blacklisted_pct = round((blacklisted * 100 / total), 2)
        self.results['blacklisted'] = blacklisted
        self.results['blacklisted_pct'] = blacklisted_pct
        logger.info(f"Blacklisted vehicles: {blacklisted} ({blacklisted_pct}%)")
        
        active = self.get_boolean_count('status.is_active', True)
        active_pct = round((active * 100 / total), 2)
        self.results['active'] = active
        self.results['active_pct'] = active_pct
        logger.info(f"Active vehicles: {active} ({active_pct}%)")
        
        # Check currently parked
        parked_query = {
            "query": {
                "exists": {
                    "field": "current_session.id"
                }
            },
            "track_total_hits": True
        }
        parked_response = self.run_query(parked_query)
        parked = parked_response['hits']['total']['value']
        parked_pct = round((parked * 100 / total), 2)
        self.results['parked'] = parked
        self.results['parked_pct'] = parked_pct
        logger.info(f"Currently parked: {parked} ({parked_pct}%)")
        
        # Get distributions
        self.results['vehicle_types'] = self.get_field_distribution('vehicle_type', 20)
        self.results['vehicle_makes'] = self.get_field_distribution('make.keyword', 10)
        
        # Calculate quality score
        quality_score = self.calculate_quality_score()
        self.results['quality_score'] = quality_score
        self.results['quality_grade'] = self.get_quality_grade(quality_score)
        
        logger.info(f"Data Quality Score: {quality_score}% - Grade: {self.results['quality_grade']}")
        
        return self.results
    
    def generate_report(self, output_file=None):
        """
        Generate a detailed quality report
        
        Args:
            output_file: Optional file path to save the report
            
        Returns:
            Formatted report string
        """
        if not self.results:
            self.run_quality_check()
        
        report = []
        report.append("=" * 50)
        report.append("VEHICLE DATA QUALITY REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 50)
        report.append("")
        
        # Summary
        report.append("SUMMARY STATISTICS:")
        report.append(f"Total vehicles: {self.results.get('total', 0)}")
        report.append("")
        
        # Quality metrics
        report.append("QUALITY METRICS:")
        report.append(f"Missing license plate: {self.results.get('missing_plate', 0)} ({self.results.get('missing_plate_pct', 0)}%)")
        report.append(f"Missing VIN: {self.results.get('missing_vin', 0)} ({self.results.get('missing_vin_pct', 0)}%)")
        report.append(f"Expired registration: {self.results.get('expired_registration', 0)} ({self.results.get('expired_registration_pct', 0)}%)")
        report.append(f"Expired insurance: {self.results.get('expired_insurance', 0)} ({self.results.get('expired_insurance_pct', 0)}%)")
        report.append(f"Blacklisted vehicles: {self.results.get('blacklisted', 0)} ({self.results.get('blacklisted_pct', 0)}%)")
        report.append(f"Active vehicles: {self.results.get('active', 0)} ({self.results.get('active_pct', 0)}%)")
        report.append(f"Currently parked: {self.results.get('parked', 0)} ({self.results.get('parked_pct', 0)}%)")
        report.append("")
        
        # Vehicle type distribution
        report.append("VEHICLE TYPE DISTRIBUTION:")
        for bucket in self.results.get('vehicle_types', []):
            report.append(f"  {bucket['key']}: {bucket['doc_count']}")
        report.append("")
        
        # Vehicle make distribution
        report.append("TOP VEHICLE MAKES:")
        for bucket in self.results.get('vehicle_makes', []):
            report.append(f"  {bucket['key']}: {bucket['doc_count']}")
        report.append("")
        
        # Quality score
        report.append("DATA QUALITY SCORE:")
        report.append(f"  Overall: {self.results.get('quality_score', 0)}%")
        report.append(f"  Grade: {self.results.get('quality_grade', 'N/A')}")
        report.append("")
        report.append("=" * 50)
        
        report_str = "\n".join(report)
        
        # Save to file if requested
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report_str)
                logger.info(f"Report saved to {output_file}")
            except Exception as e:
                logger.error(f"Error saving report: {str(e)}")
        
        return report_str
    
    def upgrade(self):
        """
        Upgrade method - runs quality check and logs results
        This is the main migration method
        """
        logger.info("Running vehicle data quality migration (upgrade)")
        
        try:
            results = self.run_quality_check()
            
            # Log critical issues
            if results.get('missing_plate_pct', 0) > 10:
                logger.warning(f"High percentage ({results['missing_plate_pct']}%) of vehicles missing license plates")
            
            if results.get('missing_vin_pct', 0) > 10:
                logger.warning(f"High percentage ({results['missing_vin_pct']}%) of vehicles missing VINs")
            
            if results.get('expired_registration', 0) > 0:
                logger.warning(f"Found {results['expired_registration']} vehicles with expired registration")
            
            if results.get('expired_insurance', 0) > 0:
                logger.warning(f"Found {results['expired_insurance']} vehicles with expired insurance")
            
            # Generate report
            report = self.generate_report(f"vehicle_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            logger.info("Quality check completed successfully")
            
            return results
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            raise
    
    def downgrade(self):
        """
        Downgrade method - can be used to revert any changes
        For this quality check migration, downgrade just logs
        """
        logger.info("Vehicle data quality migration downgrade - no changes to revert")
        return True


def run_migration(es_host='localhost', es_port=9200, auth=None, action='upgrade'):
    """
    Convenience function to run the migration
    
    Args:
        es_host: Elasticsearch host
        es_port: Elasticsearch port
        auth: Authentication tuple (username, password)
        action: 'upgrade' or 'downgrade'
    """
    migration = VehicleDataQualityMigration(
        es_host=es_host,
        es_port=es_port,
        auth=auth
    )
    
    if action == 'upgrade':
        return migration.upgrade()
    elif action == 'downgrade':
        return migration.downgrade()
    else:
        raise ValueError(f"Unknown action: {action}")


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description='Vehicle Data Quality Migration')
    parser.add_argument('--host', default='localhost', help='Elasticsearch host')
    parser.add_argument('--port', type=int, default=9200, help='Elasticsearch port')
    parser.add_argument('--user', help='Elasticsearch username')
    parser.add_argument('--password', help='Elasticsearch password')
    parser.add_argument('--action', default='upgrade', choices=['upgrade', 'downgrade'],
                       help='Migration action')
    
    args = parser.parse_args()
    
    auth = (args.user, args.password) if args.user and args.password else None
    
    run_migration(
        es_host=args.host,
        es_port=args.port,
        auth=auth,
        action=args.action
    )