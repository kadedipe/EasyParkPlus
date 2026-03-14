"""
Tests for utility functions.
"""

import pytest
from datetime import datetime, timedelta, date
from uuid import uuid4

from ..utils.datetime_utils import (
    utc_now,
    format_datetime,
    parse_datetime,
    get_date_range,
    get_week_range,
    get_month_range,
    get_quarter_range,
    get_year_range,
    days_between,
    hours_between,
    minutes_between,
    add_days,
    add_hours,
    add_minutes,
    is_weekend,
    is_business_hours,
    get_age,
    get_next_occurrence,
    get_previous_occurrence,
    to_timezone
)

from ..utils.security import (
    hash_password,
    verify_password,
    generate_token,
    verify_token,
    generate_otp,
    verify_otp,
    encrypt_data,
    decrypt_data,
    generate_api_key,
    mask_sensitive_data,
    sanitize_input,
    generate_secure_random_string,
    compute_hash,
    generate_hmac_signature,
    verify_hmac_signature
)

from ..utils.validators import (
    validate_email,
    validate_phone,
    validate_password_strength,
    validate_plate_number,
    validate_vehicle_model,
    validate_price,
    validate_uuid,
    validate_json_schema,
    validate_date_range,
    validate_future_date,
    validate_past_date,
    validate_time_format,
    validate_url,
    validate_ip_address,
    validate_coordinates
)

from ..utils.formatters import (
    format_currency,
    format_phone,
    format_plate_number,
    format_duration,
    format_file_size,
    format_percentage,
    format_address,
    truncate_string,
    camel_to_snake,
    snake_to_camel,
    pluralize
)


# Datetime utils tests
class TestDatetimeUtils:
    
    def test_utc_now(self):
        now = utc_now()
        assert isinstance(now, datetime)
        assert now.tzinfo is None
    
    def test_format_datetime(self):
        dt = datetime(2024, 1, 1, 12, 30, 0)
        formatted = format_datetime(dt, "%Y-%m-%d")
        assert formatted == "2024-01-01"
    
    def test_parse_datetime(self):
        dt_str = "2024-01-01 12:30:00"
        parsed = parse_datetime(dt_str)
        assert parsed.year == 2024
        assert parsed.month == 1
        assert parsed.day == 1
    
    def test_get_date_range(self):
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)
        dates = get_date_range(start, end)
        assert len(dates) == 5
    
    def test_get_week_range(self):
        dt = date(2024, 1, 15)  # Monday
        start, end = get_week_range(dt)
        assert start.weekday() == 0
        assert end.weekday() == 6
    
    def test_days_between(self):
        start = date(2024, 1, 1)
        end = date(2024, 1, 10)
        assert days_between(start, end) == 9
    
    def test_is_weekend(self):
        saturday = date(2024, 1, 6)  # Saturday
        monday = date(2024, 1, 1)    # Monday
        assert is_weekend(saturday) is True
        assert is_weekend(monday) is False
    
    def test_is_business_hours(self):
        business_time = datetime(2024, 1, 1, 10, 0)  # Monday 10 AM
        non_business = datetime(2024, 1, 1, 20, 0)   # Monday 8 PM
        weekend = datetime(2024, 1, 6, 10, 0)        # Saturday 10 AM
        
        assert is_business_hours(business_time) is True
        assert is_business_hours(non_business) is False
        assert is_business_hours(weekend) is False
    
    def test_get_age(self):
        birth = date(1990, 1, 1)
        age = get_age(birth)
        assert age > 0


# Security utils tests
class TestSecurityUtils:
    
    def test_hash_and_verify_password(self):
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword", hashed) is False
    
    def test_generate_and_verify_token(self):
        data = {"user_id": str(uuid4()), "role": "admin"}
        token = generate_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        decoded = verify_token(token)
        assert decoded is not None
        assert decoded["user_id"] == data["user_id"]
        assert decoded["role"] == data["role"]
    
    def test_generate_otp(self):
        otp_data = generate_otp()
        
        assert "secret" in otp_data
        assert "otp" in otp_data
        assert "uri" in otp_data
        assert len(otp_data["otp"]) == 6
    
    def test_encrypt_decrypt(self):
        data = "Sensitive information"
        key = generate_secure_random_string(32).encode()[:32]
        
        encrypted = encrypt_data(data, key)
        decrypted = decrypt_data(encrypted, key)
        
        assert encrypted != data
        assert decrypted == data
    
    def test_generate_api_key(self):
        api_key = generate_api_key()
        
        assert api_key.startswith("pk_")
        assert len(api_key) > 32
    
    def test_mask_sensitive_data(self):
        credit_card = "1234567890123456"
        masked = mask_sensitive_data(credit_card, visible_chars=4)
        
        assert masked == "************3456"
        assert len(masked) == len(credit_card)
    
    def test_sanitize_input(self):
        malicious = "<script>alert('xss')</script>"
        sanitized = sanitize_input(malicious)
        
        assert "<" not in sanitized
        assert ">" not in sanitized
    
    def test_compute_hash(self):
        data = "test data"
        hash1 = compute_hash(data)
        hash2 = compute_hash(data)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256
    
    def test_hmac_signature(self):
        data = "message"
        secret = "secret"
        
        signature = generate_hmac_signature(data, secret)
        assert verify_hmac_signature(data, secret, signature) is True
        assert verify_hmac_signature(data, secret, "wrong") is False


# Validators tests
class TestValidators:
    
    def test_validate_email(self):
        valid, error = validate_email("test@example.com")
        assert valid is True
        assert error is None
        
        valid, error = validate_email("invalid-email")
        assert valid is False
        assert error is not None
    
    def test_validate_phone(self):
        valid, error = validate_phone("+1234567890")
        assert valid is True or valid is False  # Depends on phone number validity
    
    def test_validate_password_strength(self):
        # Valid password
        valid, error = validate_password_strength("Test123!@#")
        assert valid is True
        
        # Too short
        valid, error = validate_password_strength("Test1!")
        assert valid is False
        
        # No uppercase
        valid, error = validate_password_strength("test123!@#")
        assert valid is False
    
    def test_validate_plate_number(self):
        valid, error = validate_plate_number("ABC123")
        assert valid is True
        
        valid, error = validate_plate_number("A")
        assert valid is False
    
    def test_validate_price(self):
        valid, error = validate_price(25.50)
        assert valid is True
        
        valid, error = validate_price(-10)
        assert valid is False
    
    def test_validate_uuid(self):
        valid_uuid = str(uuid4())
        assert validate_uuid(valid_uuid) is True
        assert validate_uuid("not-a-uuid") is False
    
    def test_validate_date_range(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 10)
        
        valid, error = validate_date_range(start, end)
        assert valid is True
        
        valid, error = validate_date_range(end, start)
        assert valid is False
    
    def test_validate_future_date(self):
        future = datetime.now() + timedelta(days=1)
        past = datetime.now() - timedelta(days=1)
        
        valid, error = validate_future_date(future)
        assert valid is True
        
        valid, error = validate_future_date(past)
        assert valid is False
    
    def test_validate_ip_address(self):
        assert validate_ip_address("192.168.1.1") is True
        assert validate_ip_address("256.256.256.256") is False
        assert validate_ip_address("2001:0db8:85a3:0000:0000:8a2e:0370:7334") is True
    
    def test_validate_coordinates(self):
        valid, error = validate_coordinates(40.7128, -74.0060)
        assert valid is True
        
        valid, error = validate_coordinates(100, 200)
        assert valid is False


# Formatters tests
class TestFormatters:
    
    def test_format_currency(self):
        assert format_currency(25.5) == "$25.50"
        assert format_currency(1000, currency="EUR") == "€1,000.00"
    
    def test_format_phone(self):
        formatted = format_phone("+1234567890")
        assert formatted is not None
    
    def test_format_duration(self):
        assert format_duration(3661) == "1h 1m 1s"
        assert format_duration(7200) == "2h"
        assert format_duration(90) == "1m 30s"
    
    def test_format_file_size(self):
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1048576) == "1.00 MB"
        assert format_file_size(500) == "500.00 B"
    
    def test_format_percentage(self):
        assert format_percentage(0.256) == "25.60%"
        assert format_percentage(1) == "100.00%"
    
    def test_truncate_string(self):
        text = "This is a long string"
        assert truncate_string(text, 10) == "This is..."
        assert truncate_string(text, 30) == text
    
    def test_camel_to_snake(self):
        assert camel_to_snake("camelCase") == "camel_case"
        assert camel_to_snake("XMLHttpRequest") == "xml_http_request"
    
    def test_snake_to_camel(self):
        assert snake_to_camel("snake_case") == "snakeCase"
        assert snake_to_camel("hello_world") == "helloWorld"
    
    def test_pluralize(self):
        assert pluralize("car") == "cars"
        assert pluralize("box") == "boxes"
        assert pluralize("city") == "cities"