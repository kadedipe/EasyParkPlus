# parking-management/data/migrations/versions/4d5e6f7g8h9i_add_payments.py

"""Add comprehensive payment processing system

Revision ID: 4d5e6f7g8h9i
Revises: 3c4d5e6f7g8h
Create Date: 2024-02-01 10:00:00.123456

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '4d5e6f7g8h9i'
down_revision: Union[str, None] = '3c4d5e6f7g8h'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define table names
PAYMENTS_TABLE = 'payments'
PAYMENT_METHODS_TABLE = 'payment_methods'
PAYMENT_TRANSACTIONS_TABLE = 'payment_transactions'
PAYMENT_REFUNDS_TABLE = 'payment_refunds'
PAYMENT_DISPUTES_TABLE = 'payment_disputes'
PAYMENT_FEES_TABLE = 'payment_fees'
PAYMENT_TAXES_TABLE = 'payment_taxes'
PAYMENT_RECEIPTS_TABLE = 'payment_receipts'
PAYMENT_ATTEMPTS_TABLE = 'payment_attempts'
PAYMENT_WEBHOOKS_TABLE = 'payment_webhooks'
PAYMENT_PROVIDER_CONFIGS_TABLE = 'payment_provider_configs'
PAYMENT_SETTLEMENTS_TABLE = 'payment_settlements'
PAYMENT_CURRENCY_RATES_TABLE = 'payment_currency_rates'
PAYMENT_DISCOUNT_CODES_TABLE = 'payment_discount_codes'
PAYMENT_DISCOUNT_USAGE_TABLE = 'payment_discount_usage'
PAYMENT_SUBSCRIPTIONS_TABLE = 'payment_subscriptions'
PAYMENT_INVOICES_TABLE = 'payment_invoices'
PAYMENT_INVOICE_LINES_TABLE = 'payment_invoice_lines'

# Define ENUM types for PostgreSQL
payment_status_enum = sa.Enum(
    'pending', 'processing', 'authorized', 'paid', 'failed',
    'cancelled', 'refunded', 'partially_refunded', 'disputed',
    'chargeback', 'completed', 'expired', 'voided',
    name='payment_status'
)

payment_method_type_enum = sa.Enum(
    'credit_card', 'debit_card', 'paypal', 'apple_pay', 'google_pay',
    'bank_transfer', 'cash', 'check', 'voucher', 'gift_card',
    'crypto', 'venmo', 'alipay', 'wechat_pay', 'klarna',
    'afterpay', 'affirm', 'sepa', 'ach', 'wire_transfer',
    name='payment_method_type'
)

payment_provider_enum = sa.Enum(
    'stripe', 'paypal', 'braintree', 'square', 'authorize_net',
    'adyen', 'worldpay', 'checkout_com', 'razorpay', 'payu',
    'mollie', '2checkout', 'dwolla', 'recurly', 'chargebee',
    name='payment_provider'
)

transaction_type_enum = sa.Enum(
    'sale', 'authorization', 'capture', 'void', 'refund',
    'chargeback', 'settlement', 'payout', 'fee', 'adjustment',
    name='transaction_type'
)

dispute_status_enum = sa.Enum(
    'open', 'under_review', 'won', 'lost', 'accepted',
    'waiting_for_buyer_response', 'waiting_for_seller_response',
    'appealed', 'chargeback_reversed',
    name='dispute_status'
)

dispute_reason_enum = sa.Enum(
    'fraudulent', 'duplicate', 'unauthorized', 'product_not_received',
    'product_unacceptable', 'credit_not_processed', 'cancelled_recurring',
    'bank_error', 'customer_claim', 'service_dispute',
    name='dispute_reason'
)

subscription_status_enum = sa.Enum(
    'active', 'past_due', 'canceled', 'incomplete', 'incomplete_expired',
    'trialing', 'paused', 'unpaid', 'ended',
    name='subscription_status'
)

subscription_interval_enum = sa.Enum(
    'day', 'week', 'month', 'year',
    name='subscription_interval'
)

invoice_status_enum = sa.Enum(
    'draft', 'open', 'paid', 'void', 'uncollectible',
    'overdue', 'pending', 'partially_paid',
    name='invoice_status'
)

discount_type_enum = sa.Enum(
    'percentage', 'fixed_amount', 'buy_x_get_y', 'free_shipping',
    name='discount_type'
)

discount_apply_to_enum = sa.Enum(
    'all', 'first_booking', 'recurring', 'specific_spot', 'specific_zone',
    name='discount_apply_to'
)

fee_type_enum = sa.Enum(
    'processing', 'convenience', 'service', 'late', 'cancellation',
    'foreign_transaction', 'cross_border', 'currency_conversion',
    name='fee_type'
)

currency_enum = sa.Enum(
    'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'CNY', 'INR',
    'MXN', 'BRL', 'CHF', 'HKD', 'SGD', 'NZD', 'KRW', 'SEK',
    name='currency_code'
)


def upgrade() -> None:
    """
    Upgrade migration - creates comprehensive payment system
    """
    logger.info(f"Starting migration {revision}: Add payment system")
    
    # Create ENUM types first (PostgreSQL specific)
    if op.get_context().dialect.name == 'postgresql':
        enums = [
            payment_status_enum, payment_method_type_enum, payment_provider_enum,
            transaction_type_enum, dispute_status_enum, dispute_reason_enum,
            subscription_status_enum, subscription_interval_enum, invoice_status_enum,
            discount_type_enum, discount_apply_to_enum, fee_type_enum, currency_enum
        ]
        for enum in enums:
            enum.create(op.get_bind(), checkfirst=True)
        logger.info("Created ENUM types")
    
    # Create payment methods table (saved payment methods)
    logger.info("Creating payment methods table")
    op.create_table(
        PAYMENT_METHODS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_method_type', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_payment_method_id', sa.String(255)),
        sa.Column('provider_customer_id', sa.String(255)),
        sa.Column('token', sa.String(255)),
        
        # Card details (for credit/debit cards)
        sa.Column('card_last4', sa.String(4)),
        sa.Column('card_brand', sa.String(50)),
        sa.Column('card_expiry_month', sa.Integer),
        sa.Column('card_expiry_year', sa.Integer),
        sa.Column('card_holder_name', sa.String(255)),
        sa.Column('card_fingerprint', sa.String(255)),
        sa.Column('card_country', sa.String(2)),
        sa.Column('card_funding', sa.String(20)),  # credit, debit, prepaid
        
        # Bank account details
        sa.Column('bank_account_last4', sa.String(4)),
        sa.Column('bank_account_type', sa.String(50)),  # checking, savings
        sa.Column('bank_name', sa.String(255)),
        sa.Column('bank_routing_number', sa.String(50)),
        sa.Column('bank_country', sa.String(2)),
        
        # Digital wallet details
        sa.Column('wallet_type', sa.String(50)),  # apple_pay, google_pay, paypal
        sa.Column('wallet_email', sa.String(255)),
        
        # Billing address
        sa.Column('billing_address_line1', sa.String(255)),
        sa.Column('billing_address_line2', sa.String(255)),
        sa.Column('billing_city', sa.String(100)),
        sa.Column('billing_state', sa.String(50)),
        sa.Column('billing_postal_code', sa.String(20)),
        sa.Column('billing_country', sa.String(2)),
        
        # Status
        sa.Column('is_default', sa.Boolean, server_default='false'),
        sa.Column('is_verified', sa.Boolean, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('is_expired', sa.Boolean, server_default='false'),
        sa.Column('expired_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('deactivated_at', sa.DateTime(timezone=True)),
        sa.Column('deactivation_reason', sa.String(255)),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        
        # Indexes
        sa.Index('ix_payment_methods_user', 'user_id'),
        sa.Index('ix_payment_methods_provider_id', 'provider_payment_method_id'),
        sa.Index('ix_payment_methods_token', 'token'),
        sa.Index('ix_payment_methods_card_fingerprint', 'card_fingerprint'),
        sa.Index('ix_payment_methods_is_default', 'is_default'),
        sa.Index('ix_payment_methods_is_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Saved payment methods for users'),
    )
    
    # Create payments table
    logger.info("Creating payments table")
    op.create_table(
        PAYMENTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('payment_number', sa.String(50), nullable=False, unique=True),
        sa.Column('external_id', sa.String(255), unique=True),
        
        # Relationships
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True)),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True)),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True)),
        sa.Column('payment_method_id', postgresql.UUID(as_uuid=True)),
        
        # Payment details
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('amount_refunded', sa.Numeric(10, 2), server_default='0'),
        sa.Column('amount_net', sa.Numeric(10, 2)),  # After fees
        sa.Column('amount_captured', sa.Numeric(10, 2)),
        sa.Column('amount_authorized', sa.Numeric(10, 2)),
        
        # Status
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('payment_method_type', sa.String(50)),
        sa.Column('provider', sa.String(50)),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        
        # Provider details
        sa.Column('provider_payment_id', sa.String(255)),
        sa.Column('provider_transaction_id', sa.String(255)),
        sa.Column('provider_charge_id', sa.String(255)),
        sa.Column('provider_customer_id', sa.String(255)),
        sa.Column('provider_payment_intent_id', sa.String(255)),
        sa.Column('provider_payment_method_id', sa.String(255)),
        sa.Column('provider_setup_intent_id', sa.String(255)),
        
        # Authorization
        sa.Column('authorized_at', sa.DateTime(timezone=True)),
        sa.Column('authorization_code', sa.String(255)),
        sa.Column('authorization_expires_at', sa.DateTime(timezone=True)),
        
        # Capture
        sa.Column('captured_at', sa.DateTime(timezone=True)),
        sa.Column('capture_method', sa.String(50)),  # automatic, manual
        
        # Payment timing
        sa.Column('paid_at', sa.DateTime(timezone=True)),
        sa.Column('failed_at', sa.DateTime(timezone=True)),
        sa.Column('cancelled_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        
        # Failure details
        sa.Column('failure_code', sa.String(100)),
        sa.Column('failure_message', sa.Text),
        sa.Column('failure_transaction_id', sa.String(255)),
        
        # Risk assessment
        sa.Column('risk_score', sa.Integer),
        sa.Column('risk_level', sa.String(20)),
        sa.Column('risk_factors', postgresql.JSONB),
        sa.Column('fraud_check_passed', sa.Boolean),
        sa.Column('fraud_check_details', postgresql.JSONB),
        
        # 3D Secure
        sa.Column('three_d_secure_used', sa.Boolean, server_default='false'),
        sa.Column('three_d_secure_status', sa.String(50)),
        sa.Column('three_d_secure_version', sa.String(10)),
        
        # Receipt
        sa.Column('receipt_number', sa.String(255)),
        sa.Column('receipt_url', sa.String(500)),
        sa.Column('receipt_sent', sa.Boolean, server_default='false'),
        sa.Column('receipt_sent_at', sa.DateTime(timezone=True)),
        
        # Description and metadata
        sa.Column('description', sa.String(500)),
        sa.Column('statement_descriptor', sa.String(255)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        
        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_payments_number', 'payment_number', unique=True),
        sa.Index('ix_payments_external_id', 'external_id', unique=True),
        sa.Index('ix_payments_user_id', 'user_id'),
        sa.Index('ix_payments_reservation_id', 'reservation_id'),
        sa.Index('ix_payments_subscription_id', 'subscription_id'),
        sa.Index('ix_payments_invoice_id', 'invoice_id'),
        sa.Index('ix_payments_status', 'status'),
        sa.Index('ix_payments_provider_id', 'provider_payment_id'),
        sa.Index('ix_payments_paid_at', 'paid_at'),
        sa.Index('ix_payments_created_at', 'created_at'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_method_id'], [f'{PAYMENT_METHODS_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Main payments table tracking all financial transactions'),
        
        # Partition by month
        postgresql_partition_by='RANGE (created_at)',
    )
    
    # Create payment transactions table (detailed transaction log)
    logger.info("Creating payment transactions table")
    op.create_table(
        PAYMENT_TRANSACTIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('balance_transaction_id', sa.String(255)),
        sa.Column('provider_transaction_id', sa.String(255)),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('provider_response', postgresql.JSONB),
        sa.Column('error_code', sa.String(100)),
        sa.Column('error_message', sa.Text),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_payment_transactions_payment', 'payment_id'),
        sa.Index('ix_payment_transactions_type', 'transaction_type'),
        sa.Index('ix_payment_transactions_provider_id', 'provider_transaction_id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['payment_id'], [f'{PAYMENTS_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Detailed transaction log for each payment'),
        
        # Partition by month
        postgresql_partition_by='RANGE (created_at)',
    )
    
    # Create payment refunds table
    logger.info("Creating payment refunds table")
    op.create_table(
        PAYMENT_REFUNDS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('refund_number', sa.String(50), nullable=False, unique=True),
        sa.Column('provider_refund_id', sa.String(255)),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('reason', sa.String(255)),
        sa.Column('reason_code', sa.String(100)),  # duplicate, fraudulent, customer_request
        sa.Column('status', sa.String(50), nullable=False),  # pending, succeeded, failed
        sa.Column('refund_method', sa.String(50)),  # original, balance, other
        sa.Column('failure_reason', sa.Text),
        
        # Refund timing
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        
        # Approval
        sa.Column('requires_approval', sa.Boolean, server_default='false'),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('approved_at', sa.DateTime(timezone=True)),
        sa.Column('approval_notes', sa.Text),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_refunds_payment', 'payment_id'),
        sa.Index('ix_refunds_number', 'refund_number', unique=True),
        sa.Index('ix_refunds_provider_id', 'provider_refund_id'),
        sa.Index('ix_refunds_status', 'status'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['payment_id'], [f'{PAYMENTS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Payment refunds and credits'),
    )
    
    # Create payment disputes table
    logger.info("Creating payment disputes table")
    op.create_table(
        PAYMENT_DISPUTES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_dispute_id', sa.String(255)),
        sa.Column('dispute_reason', sa.String(100), nullable=False),
        sa.Column('dispute_reason_description', sa.Text),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('evidence_due_by', sa.DateTime(timezone=True)),
        sa.Column('evidence_submitted_at', sa.DateTime(timezone=True)),
        sa.Column('evidence', postgresql.JSONB),
        sa.Column('customer_communication', sa.Text),
        sa.Column('transaction_details', postgresql.JSONB),
        
        # Timeline
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('closed_at', sa.DateTime(timezone=True)),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        
        # Outcome
        sa.Column('outcome', sa.String(50)),  # won, lost, accepted
        sa.Column('outcome_amount', sa.Numeric(10, 2)),
        sa.Column('outcome_reason', sa.Text),
        
        # Fees
        sa.Column('dispute_fee', sa.Numeric(10, 2)),
        sa.Column('dispute_fee_currency', sa.String(3)),
        sa.Column('dispute_fee_refunded', sa.Boolean, server_default='false'),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_disputes_payment', 'payment_id'),
        sa.Index('ix_disputes_provider_id', 'provider_dispute_id'),
        sa.Index('ix_disputes_status', 'status'),
        sa.Index('ix_disputes_reason', 'dispute_reason'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['payment_id'], [f'{PAYMENTS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Payment disputes and chargebacks'),
    )
    
    # Create payment fees table
    logger.info("Creating payment fees table")
    op.create_table(
        PAYMENT_FEES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fee_type', sa.String(50), nullable=False),
        sa.Column('description', sa.String(255)),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('percentage_rate', sa.Numeric(5, 2)),
        sa.Column('fixed_rate', sa.Numeric(10, 2)),
        sa.Column('provider_fee_id', sa.String(255)),
        sa.Column('is_refundable', sa.Boolean, server_default='false'),
        sa.Column('refunded_amount', sa.Numeric(10, 2), server_default='0'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_fees_payment', 'payment_id'),
        sa.Index('ix_fees_type', 'fee_type'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['payment_id'], [f'{PAYMENTS_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Fees associated with payments'),
    )
    
    # Create payment taxes table
    logger.info("Creating payment taxes table")
    op.create_table(
        PAYMENT_TAXES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tax_name', sa.String(100), nullable=False),
        sa.Column('tax_rate', sa.Numeric(5, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('tax_jurisdiction', sa.String(100)),
        sa.Column('tax_type', sa.String(50)),  # sales, vat, gst, etc.
        sa.Column('tax_number', sa.String(100)),
        sa.Column('is_recoverable', sa.Boolean, server_default='false'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_taxes_payment', 'payment_id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['payment_id'], [f'{PAYMENTS_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Taxes applied to payments'),
    )
    
    # Create payment receipts table
    logger.info("Creating payment receipts table")
    op.create_table(
        PAYMENT_RECEIPTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('receipt_number', sa.String(100), nullable=False, unique=True),
        sa.Column('receipt_url', sa.String(500)),
        sa.Column('receipt_pdf_url', sa.String(500)),
        sa.Column('receipt_html', sa.Text),
        sa.Column('receipt_data', postgresql.JSONB),
        sa.Column('sent_to_email', sa.String(255)),
        sa.Column('sent_to_phone', sa.String(20)),
        sa.Column('sent_at', sa.DateTime(timezone=True)),
        sa.Column('delivered_at', sa.DateTime(timezone=True)),
        sa.Column('opened_at', sa.DateTime(timezone=True)),
        sa.Column('downloaded_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_receipts_payment', 'payment_id'),
        sa.Index('ix_receipts_number', 'receipt_number', unique=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['payment_id'], [f'{PAYMENTS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Payment receipts and delivery tracking'),
    )
    
    # Create payment attempts table (for retry logic)
    logger.info("Creating payment attempts table")
    op.create_table(
        PAYMENT_ATTEMPTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attempt_number', sa.Integer, nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('payment_method_id', postgresql.UUID(as_uuid=True)),
        sa.Column('provider_response', postgresql.JSONB),
        sa.Column('error_code', sa.String(100)),
        sa.Column('error_message', sa.Text),
        sa.Column('error_type', sa.String(100)),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_attempts_payment', 'payment_id'),
        sa.Index('ix_attempts_status', 'status'),
        sa.Index('ix_attempts_next', 'next_attempt_at'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['payment_id'], [f'{PAYMENTS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payment_method_id'], [f'{PAYMENT_METHODS_TABLE}.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Payment retry attempts for failed payments'),
    )
    
    # Create payment webhooks table
    logger.info("Creating payment webhooks table")
    op.create_table(
        PAYMENT_WEBHOOKS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_id', sa.String(255)),
        sa.Column('provider_webhook_id', sa.String(255)),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('headers', postgresql.JSONB),
        sa.Column('signature', sa.String(255)),
        sa.Column('signature_valid', sa.Boolean),
        sa.Column('processed', sa.Boolean, server_default='false'),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
        sa.Column('processing_error', sa.Text),
        sa.Column('retry_count', sa.Integer, server_default='0'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_webhooks_provider', 'provider'),
        sa.Index('ix_webhooks_event_id', 'event_id'),
        sa.Index('ix_webhooks_processed', 'processed'),
        sa.Index('ix_webhooks_created', 'created_at'),
        
        # Table comments
        sa.Comment('Incoming webhooks from payment providers'),
    )
    
    # Create payment provider configs table
    logger.info("Creating payment provider configs table")
    op.create_table(
        PAYMENT_PROVIDER_CONFIGS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('environment', sa.String(20), nullable=False),  # test, live
        sa.Column('config_name', sa.String(100), nullable=False),
        sa.Column('api_key', sa.Text),
        sa.Column('api_secret', sa.Text),
        sa.Column('webhook_secret', sa.Text),
        sa.Column('public_key', sa.Text),
        sa.Column('private_key', sa.Text),
        sa.Column('merchant_id', sa.String(255)),
        sa.Column('store_id', sa.String(255)),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_default', sa.Boolean, server_default='false'),
        sa.Column('settings', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_provider_configs_provider', 'provider', 'environment', 'config_name', unique=True),
        sa.Index('ix_provider_configs_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Configuration for payment providers'),
    )
    
    # Create payment settlements table
    logger.info("Creating payment settlements table")
    op.create_table(
        PAYMENT_SETTLEMENTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('settlement_id', sa.String(255), unique=True),
        sa.Column('payout_id', sa.String(255)),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('payment_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column('settlement_date', sa.Date),
        sa.Column('payout_date', sa.Date),
        sa.Column('bank_account', sa.String(255)),
        sa.Column('bank_reference', sa.String(255)),
        sa.Column('fee_amount', sa.Numeric(10, 2)),
        sa.Column('net_amount', sa.Numeric(10, 2)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_settlements_provider', 'provider'),
        sa.Index('ix_settlements_id', 'settlement_id'),
        sa.Index('ix_settlements_date', 'settlement_date'),
        sa.Index('ix_settlements_status', 'status'),
        
        # Table comments
        sa.Comment('Provider settlements and payouts'),
    )
    
    # Create currency rates table
    logger.info("Creating currency rates table")
    op.create_table(
        PAYMENT_CURRENCY_RATES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('base_currency', sa.String(3), nullable=False),
        sa.Column('target_currency', sa.String(3), nullable=False),
        sa.Column('rate', sa.Numeric(10, 6), nullable=False),
        sa.Column('inverse_rate', sa.Numeric(10, 6)),
        sa.Column('source', sa.String(50)),  # provider, manual, market
        sa.Column('effective_date', sa.Date, nullable=False),
        sa.Column('expiry_date', sa.Date),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_currency_rates_pair', 'base_currency', 'target_currency', 'effective_date', unique=True),
        sa.Index('ix_currency_rates_date', 'effective_date'),
        
        # Table comments
        sa.Comment('Currency exchange rates for multi-currency support'),
    )
    
    # Create discount codes table
    logger.info("Creating discount codes table")
    op.create_table(
        PAYMENT_DISCOUNT_CODES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('discount_type', sa.String(20), nullable=False),
        sa.Column('discount_value', sa.Numeric(10, 2), nullable=False),
        sa.Column('apply_to', sa.String(20), nullable=False),
        sa.Column('minimum_amount', sa.Numeric(10, 2)),
        sa.Column('maximum_discount', sa.Numeric(10, 2)),
        sa.Column('usage_limit', sa.Integer),
        sa.Column('usage_count', sa.Integer, server_default='0'),
        sa.Column('per_user_limit', sa.Integer),
        sa.Column('first_time_only', sa.Boolean, server_default='false'),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_to', sa.DateTime(timezone=True)),
        sa.Column('days_of_week', postgresql.ARRAY(sa.Integer)),
        sa.Column('applicable_spots', postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column('applicable_zones', postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column('applicable_users', postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column('stackable', sa.Boolean, server_default='false'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_discount_codes_code', 'code', unique=True),
        sa.Index('ix_discount_codes_valid', 'valid_from', 'valid_to'),
        sa.Index('ix_discount_codes_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Discount codes and promotions'),
    )
    
    # Create discount usage table
    logger.info("Creating discount usage table")
    op.create_table(
        PAYMENT_DISCOUNT_USAGE_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('discount_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True)),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('discount_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('original_amount', sa.Numeric(10, 2)),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_discount_usage_discount', 'discount_id'),
        sa.Index('ix_discount_usage_user', 'user_id'),
        sa.Index('ix_discount_usage_reservation', 'reservation_id'),
        sa.Index('ix_discount_usage_payment', 'payment_id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['discount_id'], [f'{PAYMENT_DISCOUNT_CODES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_id'], [f'{PAYMENTS_TABLE}.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Track usage of discount codes'),
    )
    
    # Create subscriptions table
    logger.info("Creating subscriptions table")
    op.create_table(
        PAYMENT_SUBSCRIPTIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_number', sa.String(50), nullable=False, unique=True),
        sa.Column('provider_subscription_id', sa.String(255)),
        sa.Column('plan_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('interval', sa.String(20), nullable=False),
        sa.Column('interval_count', sa.Integer, server_default='1'),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('trial_amount', sa.Numeric(10, 2)),
        sa.Column('trial_period_days', sa.Integer),
        sa.Column('trial_start', sa.DateTime(timezone=True)),
        sa.Column('trial_end', sa.DateTime(timezone=True)),
        sa.Column('current_period_start', sa.DateTime(timezone=True)),
        sa.Column('current_period_end', sa.DateTime(timezone=True)),
        sa.Column('cancel_at_period_end', sa.Boolean, server_default='false'),
        sa.Column('canceled_at', sa.DateTime(timezone=True)),
        sa.Column('cancellation_reason', sa.Text),
        sa.Column('pause_mode', sa.String(50)),  # void, keep_as_draft
        sa.Column('paused_at', sa.DateTime(timezone=True)),
        sa.Column('resumed_at', sa.DateTime(timezone=True)),
        sa.Column('past_due_count', sa.Integer, server_default='0'),
        sa.Column('default_payment_method_id', postgresql.UUID(as_uuid=True)),
        sa.Column('latest_invoice_id', postgresql.UUID(as_uuid=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_subscriptions_user', 'user_id'),
        sa.Index('ix_subscriptions_number', 'subscription_number', unique=True),
        sa.Index('ix_subscriptions_provider_id', 'provider_subscription_id'),
        sa.Index('ix_subscriptions_status', 'status'),
        sa.Index('ix_subscriptions_period_end', 'current_period_end'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['default_payment_method_id'], [f'{PAYMENT_METHODS_TABLE}.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Recurring subscriptions for regular parking'),
    )
    
    # Create invoices table
    logger.info("Creating invoices table")
    op.create_table(
        PAYMENT_INVOICES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('invoice_number', sa.String(50), nullable=False, unique=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True)),
        sa.Column('provider_invoice_id', sa.String(255)),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('amount_due', sa.Numeric(10, 2), nullable=False),
        sa.Column('amount_paid', sa.Numeric(10, 2), server_default='0'),
        sa.Column('amount_remaining', sa.Numeric(10, 2)),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True)),
        sa.Column('issued_date', sa.DateTime(timezone=True)),
        sa.Column('paid_date', sa.DateTime(timezone=True)),
        sa.Column('voided_date', sa.DateTime(timezone=True)),
        sa.Column('pdf_url', sa.String(500)),
        sa.Column('invoice_data', postgresql.JSONB),
        sa.Column('billing_reason', sa.String(100)),  # subscription_create, subscription_cycle, manual
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_invoices_number', 'invoice_number', unique=True),
        sa.Index('ix_invoices_user', 'user_id'),
        sa.Index('ix_invoices_subscription', 'subscription_id'),
        sa.Index('ix_invoices_status', 'status'),
        sa.Index('ix_invoices_due_date', 'due_date'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], [f'{PAYMENT_SUBSCRIPTIONS_TABLE}.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Invoices for billing'),
    )
    
    # Create invoice lines table
    logger.info("Creating invoice lines table")
    op.create_table(
        PAYMENT_INVOICE_LINES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('quantity', sa.Integer, server_default='1'),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True)),
        sa.Column('period_end', sa.DateTime(timezone=True)),
        sa.Column('proration', sa.Boolean, server_default='false'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_invoice_lines_invoice', 'invoice_id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['invoice_id'], [f'{PAYMENT_INVOICES_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Line items for invoices'),
    )
    
    # Create functions and triggers
    logger.info("Creating database functions and triggers")
    
    # Function to generate payment number
    op.execute("""
    CREATE OR REPLACE FUNCTION generate_payment_number()
    RETURNS TRIGGER AS $$
    DECLARE
        seq_num INTEGER;
        date_prefix TEXT;
    BEGIN
        date_prefix := TO_CHAR(CURRENT_DATE, 'YYYYMMDD');
        
        SELECT COALESCE(MAX(SUBSTRING(payment_number FROM 10)::INTEGER), 0) + 1
        INTO seq_num
        FROM payments
        WHERE payment_number LIKE 'PAY-' || date_prefix || '-%';
        
        NEW.payment_number := 'PAY-' || date_prefix || '-' || LPAD(seq_num::TEXT, 6, '0');
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for payment number
    op.execute("""
    CREATE TRIGGER generate_payment_number_trigger
        BEFORE INSERT ON payments
        FOR EACH ROW
        WHEN (NEW.payment_number IS NULL)
        EXECUTE FUNCTION generate_payment_number();
    """)
    
    # Function to generate refund number
    op.execute("""
    CREATE OR REPLACE FUNCTION generate_refund_number()
    RETURNS TRIGGER AS $$
    DECLARE
        seq_num INTEGER;
        date_prefix TEXT;
    BEGIN
        date_prefix := TO_CHAR(CURRENT_DATE, 'YYYYMMDD');
        
        SELECT COALESCE(MAX(SUBSTRING(refund_number FROM 10)::INTEGER), 0) + 1
        INTO seq_num
        FROM payment_refunds
        WHERE refund_number LIKE 'REF-' || date_prefix || '-%';
        
        NEW.refund_number := 'REF-' || date_prefix || '-' || LPAD(seq_num::TEXT, 6, '0');
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for refund number
    op.execute("""
    CREATE TRIGGER generate_refund_number_trigger
        BEFORE INSERT ON payment_refunds
        FOR EACH ROW
        WHEN (NEW.refund_number IS NULL)
        EXECUTE FUNCTION generate_refund_number();
    """)
    
    # Function to generate invoice number
    op.execute("""
    CREATE OR REPLACE FUNCTION generate_invoice_number()
    RETURNS TRIGGER AS $$
    DECLARE
        seq_num INTEGER;
        date_prefix TEXT;
    BEGIN
        date_prefix := TO_CHAR(CURRENT_DATE, 'YYYYMMDD');
        
        SELECT COALESCE(MAX(SUBSTRING(invoice_number FROM 10)::INTEGER), 0) + 1
        INTO seq_num
        FROM payment_invoices
        WHERE invoice_number LIKE 'INV-' || date_prefix || '-%';
        
        NEW.invoice_number := 'INV-' || date_prefix || '-' || LPAD(seq_num::TEXT, 6, '0');
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for invoice number
    op.execute("""
    CREATE TRIGGER generate_invoice_number_trigger
        BEFORE INSERT ON payment_invoices
        FOR EACH ROW
        WHEN (NEW.invoice_number IS NULL)
        EXECUTE FUNCTION generate_invoice_number();
    """)
    
    # Function to generate subscription number
    op.execute("""
    CREATE OR REPLACE FUNCTION generate_subscription_number()
    RETURNS TRIGGER AS $$
    DECLARE
        seq_num INTEGER;
        date_prefix TEXT;
    BEGIN
        date_prefix := TO_CHAR(CURRENT_DATE, 'YYYYMM');
        
        SELECT COALESCE(MAX(SUBSTRING(subscription_number FROM 11)::INTEGER), 0) + 1
        INTO seq_num
        FROM payment_subscriptions
        WHERE subscription_number LIKE 'SUB-' || date_prefix || '-%';
        
        NEW.subscription_number := 'SUB-' || date_prefix || '-' || LPAD(seq_num::TEXT, 6, '0');
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for subscription number
    op.execute("""
    CREATE TRIGGER generate_subscription_number_trigger
        BEFORE INSERT ON payment_subscriptions
        FOR EACH ROW
        WHEN (NEW.subscription_number IS NULL)
        EXECUTE FUNCTION generate_subscription_number();
    """)
    
    # Function to update payment status based on refunds
    op.execute("""
    CREATE OR REPLACE FUNCTION update_payment_status_on_refund()
    RETURNS TRIGGER AS $$
    DECLARE
        total_payment_amount NUMERIC;
        total_refunded_amount NUMERIC;
    BEGIN
        SELECT amount INTO total_payment_amount
        FROM payments
        WHERE id = NEW.payment_id;
        
        SELECT COALESCE(SUM(amount), 0) INTO total_refunded_amount
        FROM payment_refunds
        WHERE payment_id = NEW.payment_id AND status = 'succeeded';
        
        IF total_refunded_amount >= total_payment_amount THEN
            UPDATE payments SET status = 'refunded' WHERE id = NEW.payment_id;
        ELSIF total_refunded_amount > 0 THEN
            UPDATE payments SET status = 'partially_refunded' WHERE id = NEW.payment_id;
        END IF;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for refund status updates
    op.execute("""
    CREATE TRIGGER update_payment_status_on_refund_trigger
        AFTER INSERT OR UPDATE OF status ON payment_refunds
        FOR EACH ROW
        WHEN (NEW.status = 'succeeded')
        EXECUTE FUNCTION update_payment_status_on_refund();
    """)
    
    # Function to validate discount code
    op.execute("""
    CREATE OR REPLACE FUNCTION validate_discount_code(
        p_code TEXT,
        p_user_id UUID,
        p_amount NUMERIC,
        p_spot_id UUID DEFAULT NULL
    ) RETURNS TABLE (
        valid BOOLEAN,
        discount_amount NUMERIC,
        message TEXT
    ) AS $$
    DECLARE
        v_discount RECORD;
    BEGIN
        -- Get discount code
        SELECT * INTO v_discount
        FROM payment_discount_codes
        WHERE code = p_code
            AND is_active = true
            AND valid_from <= CURRENT_TIMESTAMP
            AND (valid_to IS NULL OR valid_to >= CURRENT_TIMESTAMP);
        
        IF v_discount.id IS NULL THEN
            RETURN QUERY SELECT false, 0::NUMERIC, 'Invalid or expired discount code';
            RETURN;
        END IF;
        
        -- Check usage limit
        IF v_discount.usage_limit IS NOT NULL THEN
            IF v_discount.usage_count >= v_discount.usage_limit THEN
                RETURN QUERY SELECT false, 0::NUMERIC, 'Discount code usage limit exceeded';
                RETURN;
            END IF;
        END IF;
        
        -- Check per-user limit
        IF v_discount.per_user_limit IS NOT NULL THEN
            IF (SELECT COUNT(*) FROM payment_discount_usage 
                WHERE discount_id = v_discount.id AND user_id = p_user_id) >= v_discount.per_user_limit THEN
                RETURN QUERY SELECT false, 0::NUMERIC, 'You have already used this discount code the maximum number of times';
                RETURN;
            END IF;
        END IF;
        
        -- Check minimum amount
        IF v_discount.minimum_amount IS NOT NULL AND p_amount < v_discount.minimum_amount THEN
            RETURN QUERY SELECT false, 0::NUMERIC, 
                format('Minimum purchase amount of %s required', v_discount.minimum_amount);
            RETURN;
        END IF;
        
        -- Calculate discount amount
        IF v_discount.discount_type = 'percentage' THEN
            discount_amount := (p_amount * v_discount.discount_value / 100);
        ELSE
            discount_amount := v_discount.discount_value;
        END IF;
        
        -- Apply maximum discount
        IF v_discount.maximum_discount IS NOT NULL AND discount_amount > v_discount.maximum_discount THEN
            discount_amount := v_discount.maximum_discount;
        END IF;
        
        RETURN QUERY SELECT true, discount_amount, 'Valid discount code';
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create views
    logger.info("Creating views")
    
    # View for payment summary
    op.execute("""
    CREATE OR REPLACE VIEW v_payment_summary AS
    SELECT 
        p.id,
        p.payment_number,
        p.amount,
        p.currency,
        p.status,
        p.payment_method_type,
        p.paid_at,
        u.email as user_email,
        u.first_name || ' ' || u.last_name as user_name,
        r.reservation_number,
        COALESCE(pr.total_amount, 0) as total_refunded,
        p.amount - COALESCE(pr.total_amount, 0) as net_amount
    FROM payments p
    LEFT JOIN users u ON p.user_id = u.id
    LEFT JOIN reservations r ON p.reservation_id = r.id
    LEFT JOIN (
        SELECT payment_id, SUM(amount) as total_amount
        FROM payment_refunds
        WHERE status = 'succeeded'
        GROUP BY payment_id
    ) pr ON p.id = pr.payment_id;
    """)
    
    # View for daily revenue
    op.execute("""
    CREATE OR REPLACE VIEW v_daily_revenue AS
    SELECT 
        DATE(paid_at) as date,
        currency,
        COUNT(*) as transaction_count,
        SUM(amount) as gross_revenue,
        SUM(amount_refunded) as refunds,
        SUM(amount_net) as net_revenue,
        COUNT(DISTINCT user_id) as unique_customers
    FROM payments
    WHERE status = 'paid'
    GROUP BY DATE(paid_at), currency
    ORDER BY date DESC;
    """)
    
    # Create materialized view for revenue analytics
    op.execute("""
    CREATE MATERIALIZED VIEW mv_revenue_analytics AS
    SELECT 
        DATE_TRUNC('month', paid_at) as month,
        currency,
        COUNT(*) as total_transactions,
        SUM(amount) as total_revenue,
        SUM(amount_refunded) as total_refunds,
        SUM(amount_net) as net_revenue,
        AVG(amount) as avg_transaction_value,
        COUNT(DISTINCT user_id) as unique_customers,
        COUNT(CASE WHEN payment_method_type = 'credit_card' THEN 1 END) as credit_card_count,
        COUNT(CASE WHEN payment_method_type = 'paypal' THEN 1 END) as paypal_count,
        COUNT(CASE WHEN payment_method_type = 'cash' THEN 1 END) as cash_count
    FROM payments
    WHERE status = 'paid'
        AND paid_at >= CURRENT_DATE - INTERVAL '2 years'
    GROUP BY DATE_TRUNC('month', paid_at), currency
    ORDER BY month DESC;
    """)
    
    # Create index on materialized view
    op.create_index('idx_mv_revenue_month', 'mv_revenue_analytics', ['month'])
    
    # Insert initial data
    logger.info("Inserting initial payment data")
    
    # Insert default payment provider configs
    op.execute(f"""
    INSERT INTO {PAYMENT_PROVIDER_CONFIGS_TABLE} (
        id, provider, environment, config_name, is_default, is_active, created_at
    ) VALUES 
    (gen_random_uuid(), 'stripe', 'test', 'Stripe Test', true, true, CURRENT_TIMESTAMP),
    (gen_random_uuid(), 'paypal', 'test', 'PayPal Test', false, true, CURRENT_TIMESTAMP),
    (gen_random_uuid(), 'square', 'test', 'Square Test', false, true, CURRENT_TIMESTAMP);
    """)
    
    # Insert default discount codes
    op.execute(f"""
    INSERT INTO {PAYMENT_DISCOUNT_CODES_TABLE} (
        id, code, description, discount_type, discount_value, apply_to,
        valid_from, valid_to, is_active, created_at
    ) VALUES 
    (gen_random_uuid(), 'WELCOME10', '10% off first booking', 'percentage', 10.00, 'first_booking',
     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '1 year', true, CURRENT_TIMESTAMP),
    (gen_random_uuid(), 'SAVE5', '$5 off any booking', 'fixed_amount', 5.00, 'all',
     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '6 months', true, CURRENT_TIMESTAMP),
    (gen_random_uuid(), 'MONTHLY20', '20% off monthly subscription', 'percentage', 20.00, 'recurring',
     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '3 months', true, CURRENT_TIMESTAMP);
    """)
    
    # Insert currency rates (example)
    base_rates = [
        ('USD', 'EUR', 0.85),
        ('USD', 'GBP', 0.73),
        ('USD', 'CAD', 1.25),
        ('USD', 'JPY', 110.50),
        ('EUR', 'USD', 1.18),
        ('GBP', 'USD', 1.37),
    ]
    
    for base, target, rate in base_rates:
        op.execute(f"""
        INSERT INTO {PAYMENT_CURRENCY_RATES_TABLE} (
            id, base_currency, target_currency, rate, inverse_rate, effective_date, source
        ) VALUES (
            gen_random_uuid(), '{base}', '{target}', {rate}, {1/rate}, CURRENT_DATE, 'manual'
        );
        """)
    
    # Create partitions for high-volume tables
    logger.info("Creating partitions for payment tables")
    
    # Create partitions for payments (monthly for next 12 months)
    for i in range(12):
        month_date = datetime.now().replace(day=1) + timedelta(days=30*i)
        month_str = month_date.strftime('%Y_%m')
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS payments_{month_str} 
        PARTITION OF payments
        FOR VALUES FROM ('{month_date.strftime('%Y-%m-%d')}') 
        TO ('{next_month.strftime('%Y-%m-%d')}');
        """)
        
        # Create partition for transactions
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS payment_transactions_{month_str} 
        PARTITION OF payment_transactions
        FOR VALUES FROM ('{month_date.strftime('%Y-%m-%d')}') 
        TO ('{next_month.strftime('%Y-%m-%d')}');
        """)
    
    # Grant permissions
    if op.get_context().dialect.name == 'postgresql':
        op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;")
        op.execute("GRANT INSERT, UPDATE, DELETE ON payments, payment_methods, payment_transactions TO app_user;")
        op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;")
    
    logger.info(f"Migration {revision} completed successfully")


def downgrade() -> None:
    """
    Downgrade migration - removes payment system
    """
    logger.info(f"Starting downgrade of migration {revision}")
    
    # Drop triggers first
    logger.info("Dropping triggers")
    triggers_to_drop = [
        'generate_payment_number_trigger',
        'generate_refund_number_trigger',
        'generate_invoice_number_trigger',
        'generate_subscription_number_trigger',
        'update_payment_status_on_refund_trigger'
    ]
    for trigger in triggers_to_drop:
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON payments CASCADE;")
    
    # Drop functions
    logger.info("Dropping functions")
    functions_to_drop = [
        'generate_payment_number()',
        'generate_refund_number()',
        'generate_invoice_number()',
        'generate_subscription_number()',
        'update_payment_status_on_refund()',
        'validate_discount_code(text, uuid, numeric, uuid)'
    ]
    for func in functions_to_drop:
        op.execute(f"DROP FUNCTION IF EXISTS {func} CASCADE;")
    
    # Drop views and materialized views
    logger.info("Dropping views")
    op.execute("DROP VIEW IF EXISTS v_payment_summary CASCADE;")
    op.execute("DROP VIEW IF EXISTS v_daily_revenue CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_revenue_analytics CASCADE;")
    
    # Drop tables in reverse order
    tables_to_drop = [
        PAYMENT_INVOICE_LINES_TABLE,
        PAYMENT_INVOICES_TABLE,
        PAYMENT_SUBSCRIPTIONS_TABLE,
        PAYMENT_DISCOUNT_USAGE_TABLE,
        PAYMENT_DISCOUNT_CODES_TABLE,
        PAYMENT_CURRENCY_RATES_TABLE,
        PAYMENT_SETTLEMENTS_TABLE,
        PAYMENT_PROVIDER_CONFIGS_TABLE,
        PAYMENT_WEBHOOKS_TABLE,
        PAYMENT_ATTEMPTS_TABLE,
        PAYMENT_RECEIPTS_TABLE,
        PAYMENT_TAXES_TABLE,
        PAYMENT_FEES_TABLE,
        PAYMENT_DISPUTES_TABLE,
        PAYMENT_REFUNDS_TABLE,
        PAYMENT_TRANSACTIONS_TABLE,
        PAYMENTS_TABLE,
        PAYMENT_METHODS_TABLE,
    ]
    
    for table in tables_to_drop:
        logger.info(f"Dropping {table} table")
        op.drop_table(table)
    
    # Drop ENUM types
    if op.get_context().dialect.name == 'postgresql':
        enums_to_drop = [
            'payment_status', 'payment_method_type', 'payment_provider',
            'transaction_type', 'dispute_status', 'dispute_reason',
            'subscription_status', 'subscription_interval', 'invoice_status',
            'discount_type', 'discount_apply_to', 'fee_type', 'currency_code'
        ]
        for enum in enums_to_drop:
            logger.info(f"Dropping {enum} enum")
            op.execute(f"DROP TYPE IF EXISTS {enum} CASCADE;")
    
    # Drop partitions
    logger.info("Dropping partitions")
    for i in range(12):
        month_date = datetime.now().replace(day=1) + timedelta(days=30*i)
        month_str = month_date.strftime('%Y_%m')
        op.execute(f"DROP TABLE IF EXISTS payments_{month_str} CASCADE;")
        op.execute(f"DROP TABLE IF EXISTS payment_transactions_{month_str} CASCADE;")
    
    logger.info(f"Downgrade of migration {revision} completed successfully")


def validate_payment_data() -> dict:
    """
    Validate payment data quality after migration
    """
    logger.info("Validating payment data quality")
    
    connection = op.get_bind()
    results = {}
    
    # Check for payments with mismatched totals
    result = connection.execute("""
        SELECT COUNT(*)
        FROM payments p
        LEFT JOIN payment_refunds pr ON p.id = pr.payment_id AND pr.status = 'succeeded'
        WHERE p.amount_refunded != COALESCE((
            SELECT SUM(amount) FROM payment_refunds 
            WHERE payment_id = p.id AND status = 'succeeded'
        ), 0);
    """)
    results['mismatched_refund_amounts'] = result.scalar()
    
    # Check for orphaned payment methods
    result = connection.execute("""
        SELECT COUNT(*)
        FROM payment_methods pm
        LEFT JOIN users u ON pm.user_id = u.id
        WHERE u.id IS NULL;
    """)
    results['orphaned_payment_methods'] = result.scalar()
    
    # Check for payments without transactions
    result = connection.execute("""
        SELECT COUNT(*)
        FROM payments p
        LEFT JOIN payment_transactions pt ON p.id = pt.payment_id
        WHERE pt.id IS NULL;
    """)
    results['payments_without_transactions'] = result.scalar()
    
    # Check for expired discount codes still marked active
    result = connection.execute("""
        SELECT COUNT(*)
        FROM payment_discount_codes
        WHERE is_active = true
            AND valid_to < CURRENT_DATE;
    """)
    results['expired_active_discounts'] = result.scalar()
    
    # Check for subscriptions with missing invoices
    result = connection.execute("""
        SELECT COUNT(*)
        FROM payment_subscriptions ps
        LEFT JOIN payment_invoices pi ON ps.id = pi.subscription_id
        WHERE ps.status = 'active'
            AND pi.id IS NULL;
    """)
    results['active_subscriptions_without_invoices'] = result.scalar()
    
    logger.info(f"Validation results: {results}")
    return results


def post_upgrade_hook():
    """Hook to run after successful upgrade"""
    logger.info("Running post-upgrade hooks for payments migration")
    
    # Validate the migration
    validation_results = validate_payment_data()
    
    # Refresh materialized view
    op.execute("REFRESH MATERIALIZED VIEW mv_revenue_analytics;")
    
    # Log any issues
    for key, value in validation_results.items():
        if value > 0:
            logger.warning(f"Validation issue - {key}: {value}")
    
    # Log summary statistics
    connection = op.get_bind()
    stats = connection.execute("""
        SELECT 
            COUNT(*) as total_payments,
            COALESCE(SUM(amount), 0) as total_amount,
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(DISTINCT payment_method_type) as payment_methods_used
        FROM payments
    """).first()
    
    if stats:
        logger.info(f"Payment Summary: {stats.total_payments} total payments, "
                   f"${stats.total_amount} total amount, {stats.unique_users} users")
    
    logger.info("Payments system migration completed successfully")


# Register the post-upgrade hook
if hasattr(op, 'register_post_upgrade_hook'):
    op.register_post_upgrade_hook(post_upgrade_hook)


# Add table comments
def add_table_comments():
    """Add detailed comments to tables for documentation"""
    op.execute(f"""
    COMMENT ON TABLE {PAYMENTS_TABLE} IS 'Core payments table tracking all financial transactions with support for multiple payment methods, providers, and statuses.';
    COMMENT ON TABLE {PAYMENT_METHODS_TABLE} IS 'Saved payment methods for users including credit cards, bank accounts, and digital wallets with PCI compliance.';
    COMMENT ON TABLE {PAYMENT_TRANSACTIONS_TABLE} IS 'Detailed transaction log for each payment including provider responses and error tracking.';
    COMMENT ON TABLE {PAYMENT_REFUNDS_TABLE} IS 'Payment refunds with approval workflow and provider integration.';
    COMMENT ON TABLE {PAYMENT_DISPUTES_TABLE} IS 'Dispute and chargeback management with evidence tracking.';
    COMMENT ON TABLE {PAYMENT_FEES_TABLE} IS 'Fee breakdown for each payment including processing fees, currency conversion, etc.';
    COMMENT ON TABLE {PAYMENT_TAXES_TABLE} IS 'Tax information for payments supporting multiple tax jurisdictions.';
    COMMENT ON TABLE {PAYMENT_RECEIPTS_TABLE} IS 'Payment receipts with delivery tracking and multiple format support.';
    COMMENT ON TABLE {PAYMENT_ATTEMPTS_TABLE} IS 'Retry attempts for failed payments with scheduling.';
    COMMENT ON TABLE {PAYMENT_WEBHOOKS_TABLE} IS 'Incoming webhooks from payment providers with validation and processing status.';
    COMMENT ON TABLE {PAYMENT_PROVIDER_CONFIGS_TABLE} IS 'Configuration for payment providers supporting multiple environments.';
    COMMENT ON TABLE {PAYMENT_SETTLEMENTS_TABLE} IS 'Provider settlements and payouts for reconciliation.';
    COMMENT ON TABLE {PAYMENT_CURRENCY_RATES_TABLE} IS 'Currency exchange rates for multi-currency support.';
    COMMENT ON TABLE {PAYMENT_DISCOUNT_CODES_TABLE} IS 'Discount codes and promotions with usage limits and conditions.';
    COMMENT ON TABLE {PAYMENT_DISCOUNT_USAGE_TABLE} IS 'Usage tracking for discount codes to prevent abuse.';
    COMMENT ON TABLE {PAYMENT_SUBSCRIPTIONS_TABLE} IS 'Recurring subscriptions for regular parking with trial periods and pause/resume.';
    COMMENT ON TABLE {PAYMENT_INVOICES_TABLE} IS 'Invoices for billing with PDF generation and payment tracking.';
    COMMENT ON TABLE {PAYMENT_INVOICE_LINES_TABLE} IS 'Line items for invoices supporting prorated charges.';
    """)