"""Mock data fixtures for parking management system tests."""

import pytest
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Any, Optional, Union, Callable
from unittest.mock import Mock, MagicMock, AsyncMock, PropertyMock
import random
import string
import json
from decimal import Decimal

# ============================================================================
# Basic Mock Object Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = MagicMock()
    
    # Mock common session methods
    mock_session.add = MagicMock()
    mock_session.add_all = MagicMock()
    mock_session.delete = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.rollback = MagicMock()
    mock_session.flush = MagicMock()
    mock_session.refresh = MagicMock()
    mock_session.close = MagicMock()
    
    # Mock query methods
    mock_query = MagicMock()
    mock_query.filter = MagicMock(return_value=mock_query)
    mock_query.filter_by = MagicMock(return_value=mock_query)
    mock_query.join = MagicMock(return_value=mock_query)
    mock_query.outerjoin = MagicMock(return_value=mock_query)
    mock_query.order_by = MagicMock(return_value=mock_query)
    mock_query.group_by = MagicMock(return_value=mock_query)
    mock_query.limit = MagicMock(return_value=mock_query)
    mock_query.offset = MagicMock(return_value=mock_query)
    mock_query.all = MagicMock(return_value=[])
    mock_query.first = MagicMock(return_value=None)
    mock_query.one = MagicMock(return_value=None)
    mock_query.one_or_none = MagicMock(return_value=None)
    mock_query.count = MagicMock(return_value=0)
    mock_query.update = MagicMock(return_value=1)
    mock_query.delete = MagicMock(return_value=1)
    
    mock_session.query = MagicMock(return_value=mock_query)
    
    return mock_session


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    mock_redis = MagicMock()
    
    # String operations
    mock_redis.get = MagicMock(return_value=None)
    mock_redis.set = MagicMock(return_value=True)
    mock_redis.setex = MagicMock(return_value=True)
    mock_redis.setnx = MagicMock(return_value=True)
    mock_redis.mset = MagicMock(return_value=True)
    mock_redis.mget = MagicMock(return_value=[])
    mock_redis.delete = MagicMock(return_value=1)
    mock_redis.exists = MagicMock(return_value=0)
    mock_redis.expire = MagicMock(return_value=True)
    mock_redis.ttl = MagicMock(return_value=-1)
    
    # Hash operations
    mock_redis.hset = MagicMock(return_value=1)
    mock_redis.hget = MagicMock(return_value=None)
    mock_redis.hgetall = MagicMock(return_value={})
    mock_redis.hdel = MagicMock(return_value=1)
    mock_redis.hexists = MagicMock(return_value=False)
    mock_redis.hkeys = MagicMock(return_value=[])
    mock_redis.hvals = MagicMock(return_value=[])
    mock_redis.hlen = MagicMock(return_value=0)
    
    # List operations
    mock_redis.lpush = MagicMock(return_value=1)
    mock_redis.rpush = MagicMock(return_value=1)
    mock_redis.lpop = MagicMock(return_value=None)
    mock_redis.rpop = MagicMock(return_value=None)
    mock_redis.llen = MagicMock(return_value=0)
    mock_redis.lrange = MagicMock(return_value=[])
    
    # Set operations
    mock_redis.sadd = MagicMock(return_value=1)
    mock_redis.srem = MagicMock(return_value=1)
    mock_redis.smembers = MagicMock(return_value=set())
    mock_redis.sismember = MagicMock(return_value=False)
    mock_redis.scard = MagicMock(return_value=0)
    
    # Sorted set operations
    mock_redis.zadd = MagicMock(return_value=1)
    mock_redis.zrem = MagicMock(return_value=1)
    mock_redis.zrange = MagicMock(return_value=[])
    mock_redis.zrevrange = MagicMock(return_value=[])
    mock_redis.zcard = MagicMock(return_value=0)
    mock_redis.zscore = MagicMock(return_value=None)
    
    # Pub/Sub
    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = MagicMock()
    mock_pubsub.publish = MagicMock(return_value=1)
    mock_pubsub.listen = MagicMock(return_value=[])
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    mock_redis.publish = MagicMock(return_value=1)
    
    # Pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.execute = MagicMock(return_value=[])
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
    
    # Connection management
    mock_redis.ping = MagicMock(return_value=True)
    mock_redis.close = MagicMock()
    mock_redis.connection_pool = MagicMock()
    
    return mock_redis


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    mock_s3 = MagicMock()
    
    # Bucket operations
    mock_s3.create_bucket = MagicMock()
    mock_s3.delete_bucket = MagicMock()
    mock_s3.list_buckets = MagicMock(return_value={'Buckets': []})
    mock_s3.head_bucket = MagicMock()
    
    # Object operations
    mock_s3.put_object = MagicMock()
    mock_s3.get_object = MagicMock(return_value={
        'Body': MagicMock(read=MagicMock(return_value=b'test data')),
        'ContentLength': 9,
        'ContentType': 'text/plain'
    })
    mock_s3.delete_object = MagicMock()
    mock_s3.delete_objects = MagicMock()
    mock_s3.copy_object = MagicMock()
    mock_s3.head_object = MagicMock()
    mock_s3.list_objects = MagicMock(return_value={'Contents': []})
    mock_s3.list_objects_v2 = MagicMock(return_value={'Contents': []})
    
    # Multipart upload
    mock_s3.create_multipart_upload = MagicMock(return_value={'UploadId': 'test-upload-id'})
    mock_s3.upload_part = MagicMock()
    mock_s3.complete_multipart_upload = MagicMock()
    mock_s3.abort_multipart_upload = MagicMock()
    
    # Presigned URLs
    mock_s3.generate_presigned_url = MagicMock(return_value='https://test-url.com')
    mock_s3.generate_presigned_post = MagicMock(return_value={
        'url': 'https://test-url.com',
        'fields': {}
    })
    
    return mock_s3


@pytest.fixture
def mock_sqs_client():
    """Create a mock SQS client."""
    mock_sqs = MagicMock()
    
    # Queue operations
    mock_sqs.create_queue = MagicMock(return_value={'QueueUrl': 'https://test-queue-url'})
    mock_sqs.get_queue_url = MagicMock(return_value={'QueueUrl': 'https://test-queue-url'})
    mock_sqs.delete_queue = MagicMock()
    mock_sqs.list_queues = MagicMock(return_value={'QueueUrls': []})
    mock_sqs.purge_queue = MagicMock()
    
    # Message operations
    mock_sqs.send_message = MagicMock(return_value={'MessageId': 'test-message-id'})
    mock_sqs.send_message_batch = MagicMock(return_value={'Successful': []})
    mock_sqs.receive_message = MagicMock(return_value={'Messages': []})
    mock_sqs.delete_message = MagicMock()
    mock_sqs.delete_message_batch = MagicMock(return_value={'Successful': []})
    mock_sqs.change_message_visibility = MagicMock()
    
    # Queue attributes
    mock_sqs.get_queue_attributes = MagicMock(return_value={'Attributes': {}})
    mock_sqs.set_queue_attributes = MagicMock()
    
    return mock_sqs


@pytest.fixture
def mock_sns_client():
    """Create a mock SNS client."""
    mock_sns = MagicMock()
    
    # Topic operations
    mock_sns.create_topic = MagicMock(return_value={'TopicArn': 'arn:aws:sns:test-topic'})
    mock_sns.delete_topic = MagicMock()
    mock_sns.list_topics = MagicMock(return_value={'Topics': []})
    mock_sns.get_topic_attributes = MagicMock(return_value={'Attributes': {}})
    mock_sns.set_topic_attributes = MagicMock()
    
    # Subscription operations
    mock_sns.subscribe = MagicMock(return_value={'SubscriptionArn': 'test-subscription-arn'})
    mock_sns.unsubscribe = MagicMock()
    mock_sns.list_subscriptions = MagicMock(return_value={'Subscriptions': []})
    mock_sns.list_subscriptions_by_topic = MagicMock(return_value={'Subscriptions': []})
    
    # Publish
    mock_sns.publish = MagicMock(return_value={'MessageId': 'test-message-id'})
    mock_sns.publish_batch = MagicMock(return_value={'Successful': []})
    
    # SMS
    mock_sns.check_if_phone_number_is_opted_out = MagicMock(return_value={'isOptedOut': False})
    mock_sns.opt_in_phone_number = MagicMock()
    
    return mock_sns


@pytest.fixture
def mock_email_service():
    """Create a mock email service."""
    mock_email = MagicMock()
    
    # Send methods
    mock_email.send = MagicMock(return_value={'id': 'email-123', 'status': 'sent'})
    mock_email.send_batch = MagicMock(return_value=[{'id': f'email-{i}', 'status': 'sent'} for i in range(3)])
    mock_email.send_template = MagicMock(return_value={'id': 'email-123', 'status': 'sent'})
    mock_email.send_with_attachments = MagicMock(return_value={'id': 'email-123', 'status': 'sent'})
    
    # Template methods
    mock_email.create_template = MagicMock(return_value={'TemplateName': 'test-template'})
    mock_email.delete_template = MagicMock()
    mock_email.list_templates = MagicMock(return_value={'TemplatesMetadata': []})
    mock_email.get_template = MagicMock(return_value={'Template': {}})
    mock_email.update_template = MagicMock()
    
    # Verification
    mock_email.verify_email = MagicMock(return_value=True)
    mock_email.verify_domain = MagicMock(return_value=True)
    mock_email.list_verified_emails = MagicMock(return_value=[])
    
    # Statistics
    mock_email.get_send_statistics = MagicMock(return_value={'SendDataPoints': []})
    mock_email.get_send_quota = MagicMock(return_value={
        'Max24HourSend': 1000,
        'MaxSendRate': 10,
        'SentLast24Hours': 100
    })
    
    # Configuration
    mock_email.configuration_set = MagicMock()
    
    return mock_email


@pytest.fixture
def mock_sms_service():
    """Create a mock SMS service."""
    mock_sms = MagicMock()
    
    # Send methods
    mock_sms.send = MagicMock(return_value={
        'id': 'sms-123',
        'status': 'sent',
        'to': '+1234567890',
        'segments': 1
    })
    mock_sms.send_batch = MagicMock(return_value=[
        {'id': f'sms-{i}', 'status': 'sent'} for i in range(3)
    ])
    
    # Status
    mock_sms.get_status = MagicMock(return_value={
        'id': 'sms-123',
        'status': 'delivered',
        'delivered_at': datetime.now().isoformat()
    })
    
    # Balance
    mock_sms.get_balance = MagicMock(return_value={
        'balance': 100.50,
        'currency': 'USD'
    })
    
    # Templates
    mock_sms.create_template = MagicMock(return_value={'id': 'template-123'})
    mock_sms.delete_template = MagicMock()
    
    # Opt-out management
    mock_sms.check_opt_out = MagicMock(return_value=False)
    mock_sms.opt_out = MagicMock()
    mock_sms.opt_in = MagicMock()
    
    return mock_sms


@pytest.fixture
def mock_push_notification_service():
    """Create a mock push notification service."""
    mock_push = MagicMock()
    
    # Send methods
    mock_push.send_to_device = MagicMock(return_value={
        'id': 'push-123',
        'status': 'sent',
        'device_token': 'device-token-123'
    })
    mock_push.send_to_topic = MagicMock(return_value={
        'id': 'push-456',
        'status': 'sent',
        'topic': 'test-topic'
    })
    mock_push.send_batch = MagicMock(return_value=[
        {'id': f'push-{i}', 'status': 'sent'} for i in range(5)
    ])
    
    # Device management
    mock_push.register_device = MagicMock(return_value={'device_id': 'device-123'})
    mock_push.unregister_device = MagicMock()
    mock_push.list_devices = MagicMock(return_value=[])
    
    # Topic management
    mock_push.create_topic = MagicMock(return_value={'topic_arn': 'arn:test-topic'})
    mock_push.delete_topic = MagicMock()
    mock_push.subscribe_to_topic = MagicMock()
    mock_push.unsubscribe_from_topic = MagicMock()
    mock_push.list_topics = MagicMock(return_value=[])
    
    # Templates
    mock_push.create_template = MagicMock()
    mock_push.delete_template = MagicMock()
    
    return mock_push


@pytest.fixture
def mock_payment_gateway():
    """Create a mock payment gateway."""
    mock_gateway = MagicMock()
    
    # Payment methods
    mock_gateway.charge = MagicMock(return_value={
        'id': 'ch_test123',
        'object': 'charge',
        'amount': 2000,
        'currency': 'usd',
        'status': 'succeeded',
        'paid': True,
        'payment_method_details': {
            'card': {
                'brand': 'visa',
                'last4': '4242'
            }
        }
    })
    
    mock_gateway.refund = MagicMock(return_value={
        'id': 're_test123',
        'object': 'refund',
        'amount': 2000,
        'currency': 'usd',
        'status': 'succeeded'
    })
    
    # Customer methods
    mock_gateway.create_customer = MagicMock(return_value={
        'id': 'cus_test123',
        'email': 'test@example.com',
        'metadata': {}
    })
    mock_gateway.get_customer = MagicMock(return_value={
        'id': 'cus_test123',
        'email': 'test@example.com'
    })
    mock_gateway.update_customer = MagicMock()
    mock_gateway.delete_customer = MagicMock()
    
    # Payment method management
    mock_gateway.attach_payment_method = MagicMock()
    mock_gateway.detach_payment_method = MagicMock()
    mock_gateway.list_payment_methods = MagicMock(return_value={'data': []})
    
    # Subscription methods
    mock_gateway.create_subscription = MagicMock(return_value={
        'id': 'sub_test123',
        'status': 'active'
    })
    mock_gateway.cancel_subscription = MagicMock()
    mock_gateway.update_subscription = MagicMock()
    
    # Webhook handling
    mock_gateway.construct_webhook_event = MagicMock(return_value={
        'type': 'payment_intent.succeeded',
        'data': {'object': {}}
    })
    
    # Error simulation
    mock_gateway.simulate_failure = MagicMock(side_effect=Exception("Payment failed"))
    
    return mock_gateway


@pytest.fixture
def mock_geocoding_service():
    """Create a mock geocoding service."""
    mock_geo = MagicMock()
    
    # Geocoding
    mock_geo.geocode = MagicMock(return_value={
        'latitude': 37.7749,
        'longitude': -122.4194,
        'formatted_address': '123 Main St, San Francisco, CA 94105',
        'place_id': 'place_123',
        'accuracy': 'ROOFTOP'
    })
    
    mock_geo.reverse_geocode = MagicMock(return_value={
        'formatted_address': '123 Main St, San Francisco, CA 94105',
        'street_number': '123',
        'street_name': 'Main St',
        'city': 'San Francisco',
        'state': 'CA',
        'postal_code': '94105',
        'country': 'USA'
    })
    
    # Distance calculation
    mock_geo.calculate_distance = MagicMock(return_value={
        'distance': 1.5,  # miles
        'duration': 300,   # seconds
        'mode': 'driving'
    })
    
    # Batch operations
    mock_geo.batch_geocode = MagicMock(return_value=[
        {'latitude': 37.7749, 'longitude': -122.4194},
        {'latitude': 37.7750, 'longitude': -122.4195}
    ])
    
    # Place search
    mock_geo.search_places = MagicMock(return_value=[
        {'place_id': 'place_1', 'name': 'Place 1'},
        {'place_id': 'place_2', 'name': 'Place 2'}
    ])
    
    # Place details
    mock_geo.get_place_details = MagicMock(return_value={
        'place_id': 'place_123',
        'name': 'Test Location',
        'rating': 4.5,
        'reviews': 100
    })
    
    # Autocomplete
    mock_geo.autocomplete = MagicMock(return_value=[
        {'description': '123 Main St, San Francisco, CA'},
        {'description': '123 Market St, San Francisco, CA'}
    ])
    
    return mock_geo


@pytest.fixture
def mock_qr_code_generator():
    """Create a mock QR code generator."""
    mock_qr = MagicMock()
    
    # Generate QR code
    mock_qr.generate = MagicMock(return_value={
        'image': b'fake_png_data',
        'data': 'test-data',
        'format': 'PNG',
        'size': 1024
    })
    
    # Generate with logo
    mock_qr.generate_with_logo = MagicMock(return_value={
        'image': b'fake_png_data_with_logo',
        'data': 'test-data',
        'format': 'PNG',
        'size': 2048
    })
    
    # Generate as SVG
    mock_qr.generate_svg = MagicMock(return_value='<svg>...</svg>')
    
    # Generate as ASCII
    mock_qr.generate_ascii = MagicMock(return_value='████████\n████████')
    
    # Decode QR code
    mock_qr.decode = MagicMock(return_value={
        'data': 'decoded-data',
        'format': 'QR_CODE'
    })
    
    # Batch generation
    mock_qr.generate_batch = MagicMock(return_value=[
        {'data': 'data1', 'image': b'image1'},
        {'data': 'data2', 'image': b'image2'}
    ])
    
    # Style options
    mock_qr.set_style = MagicMock()
    mock_qr.set_colors = MagicMock()
    
    return mock_qr


@pytest.fixture
def mock_parking_gate_controller():
    """Create a mock parking gate controller."""
    mock_gate = MagicMock()
    
    # Gate operations
    mock_gate.open_entry_gate = MagicMock(return_value={
        'success': True,
        'gate_id': 'entry-1',
        'timestamp': datetime.now().isoformat()
    })
    
    mock_gate.open_exit_gate = MagicMock(return_value={
        'success': True,
        'gate_id': 'exit-1',
        'timestamp': datetime.now().isoformat()
    })
    
    mock_gate.close_gate = MagicMock(return_value={
        'success': True,
        'gate_id': 'gate-1',
        'timestamp': datetime.now().isoformat()
    })
    
    # Gate status
    mock_gate.get_status = MagicMock(return_value={
        'gate_id': 'entry-1',
        'is_open': False,
        'is_obstructed': False,
        'last_operation': datetime.now().isoformat(),
        'battery_level': 85
    })
    
    mock_gate.get_all_gates_status = MagicMock(return_value=[
        {'gate_id': 'entry-1', 'is_open': False},
        {'gate_id': 'entry-2', 'is_open': True},
        {'gate_id': 'exit-1', 'is_open': False}
    ])
    
    # Obstruction detection
    mock_gate.check_obstruction = MagicMock(return_value={
        'is_obstructed': False,
        'obstruction_type': None,
        'timestamp': datetime.now().isoformat()
    })
    
    # Manual override
    mock_gate.manual_override = MagicMock(return_value={
        'success': True,
        'mode': 'manual',
        'activated_by': 'operator-1'
    })
    
    # Emergency operations
    mock_gate.emergency_open_all = MagicMock(return_value={
        'success': True,
        'gates_affected': 5,
        'timestamp': datetime.now().isoformat()
    })
    
    mock_gate.emergency_close_all = MagicMock(return_value={
        'success': True,
        'gates_affected': 5,
        'timestamp': datetime.now().isoformat()
    })
    
    # Maintenance mode
    mock_gate.enter_maintenance_mode = MagicMock()
    mock_gate.exit_maintenance_mode = MagicMock()
    mock_gate.is_in_maintenance = MagicMock(return_value=False)
    
    return mock_gate


@pytest.fixture
def mock_lpr_camera():
    """Create a mock license plate recognition camera."""
    mock_lpr = MagicMock()
    
    # Capture and recognize
    mock_lpr.capture_image = MagicMock(return_value=b'fake_image_data')
    mock_lpr.recognize_plate = MagicMock(return_value={
        'plate_number': 'ABC123',
        'confidence': 0.95,
        'timestamp': datetime.now().isoformat(),
        'image': b'fake_image_data'
    })
    
    # Video stream
    mock_lpr.start_video_stream = MagicMock()
    mock_lpr.stop_video_stream = MagicMock()
    
    # Camera status
    mock_lpr.get_status = MagicMock(return_value={
        'camera_id': 'lpr-1',
        'is_operational': True,
        'last_recognition': datetime.now().isoformat(),
        'error_code': None
    })
    
    return mock_lpr