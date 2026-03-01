"""Payment model for the parking management system.

This module defines the Payment model which represents financial transactions
for parking reservations, including processing, refunds, and payment tracking.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import uuid
import hmac
import hashlib
import json

from ..enums import PaymentStatus


class PaymentMethod(str, Enum):
    """Payment method types."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO = "crypto"
    GIFT_CARD = "gift_card"
    LOYALTY_POINTS = "loyalty_points"


class PaymentProvider(str, Enum):
    """Payment provider types."""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    BRAINTREE = "braintree"
    AUTHORIZE_NET = "authorize_net"
    SQUARE = "square"
    ADYEN = "adyen"
    INTERNAL = "internal"  # For cash or manual payments


class PaymentType(str, Enum):
    """Payment type classifications."""
    RESERVATION = "reservation"
    DEPOSIT = "deposit"
    MEMBERSHIP = "membership"
    FEE = "fee"
    FINE = "fine"
    REFUND = "refund"


class Currency(str, Enum):
    """Supported currencies."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"


class Payment:
    """Payment model representing a financial transaction.
    
    A payment is associated with a reservation and user, and tracks the
    entire lifecycle of a transaction including authorization, capture,
    and potential refunds.
    
    Attributes:
        payment_id: Unique identifier for the payment
        reservation_id: ID of the associated reservation
        user_id: ID of the user making the payment
        amount: Payment amount
        currency: Currency code (USD, EUR, etc.)
        status: Current payment status
        payment_method: Method used for payment
        payment_type: Type of payment (reservation, deposit, etc.)
        provider: Payment service provider
        transaction_id: External transaction ID from provider
        provider_response: Raw response from payment provider
        error_message: Error message if payment failed
        refunded_amount: Total amount refunded
        refund_reason: Reason for refund if applicable
        payment_date: When the payment was processed
        created_at: When the payment record was created
        updated_at: When the payment was last updated
        metadata: Additional payment metadata
        receipt_url: URL to payment receipt
        invoice_number: Generated invoice number
        billing_address: Billing address for the payment
        card_last_four: Last 4 digits of card if applicable
        card_brand: Card brand (Visa, Mastercard, etc.)
    """
    
    def __init__(
        self,
        payment_id: Optional[int] = None,
        reservation_id: Optional[int] = None,
        user_id: int = 0,
        amount: float = 0.0,
        currency: Currency = Currency.USD,
        status: PaymentStatus = PaymentStatus.PENDING,
        payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD,
        payment_type: PaymentType = PaymentType.RESERVATION,
        provider: PaymentProvider = PaymentProvider.INTERNAL,
        transaction_id: Optional[str] = None,
        provider_response: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        refunded_amount: float = 0.0,
        refund_reason: Optional[str] = None,
        payment_date: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        receipt_url: Optional[str] = None,
        invoice_number: Optional[str] = None,
        billing_address: Optional[Dict[str, str]] = None,
        card_last_four: Optional[str] = None,
        card_brand: Optional[str] = None,
    ):
        """Initialize a new Payment instance.
        
        Args:
            payment_id: Unique identifier for the payment
            reservation_id: ID of associated reservation
            user_id: ID of user making payment
            amount: Payment amount
            currency: Currency code
            status: Payment status
            payment_method: Method used
            payment_type: Type of payment
            provider: Payment provider
            transaction_id: External transaction ID
            provider_response: Raw provider response
            error_message: Error message if failed
            refunded_amount: Amount refunded
            refund_reason: Reason for refund
            payment_date: When payment was processed
            created_at: Record creation timestamp
            updated_at: Last update timestamp
            metadata: Additional metadata
            receipt_url: URL to receipt
            invoice_number: Generated invoice number
            billing_address: Billing address
            card_last_four: Last 4 digits of card
            card_brand: Card brand
        """
        self.payment_id = payment_id
        self.reservation_id = reservation_id
        self.user_id = user_id
        self.amount = round(amount, 2)  # Ensure 2 decimal places
        self.currency = currency
        self.status = status
        self.payment_method = payment_method
        self.payment_type = payment_type
        self.provider = provider
        self.transaction_id = transaction_id or self._generate_transaction_id()
        self.provider_response = provider_response or {}
        self.error_message = error_message
        self.refunded_amount = round(refunded_amount, 2)
        self.refund_reason = refund_reason
        self.payment_date = payment_date
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at
        self.metadata = metadata or {}
        self.receipt_url = receipt_url
        self.invoice_number = invoice_number or self._generate_invoice_number()
        self.billing_address = billing_address or {}
        self.card_last_four = card_last_four
        self.card_brand = card_brand
        
        # Set payment date to now if status is PAID and no date provided
        if self.status == PaymentStatus.PAID and not self.payment_date:
            self.payment_date = datetime.utcnow()
    
    def __repr__(self) -> str:
        """String representation of the payment."""
        return f"<Payment {self.payment_id}: {self.amount} {self.currency.value} ({self.status.value})>"
    
    def __str__(self) -> str:
        """User-friendly string representation."""
        return f"Payment {self.invoice_number}: {self.amount} {self.currency.value}"
    
    @property
    def is_successful(self) -> bool:
        """Check if payment was successful."""
        return self.status == PaymentStatus.PAID
    
    @property
    def is_pending(self) -> bool:
        """Check if payment is pending."""
        return self.status == PaymentStatus.PENDING
    
    @property
    def is_failed(self) -> bool:
        """Check if payment failed."""
        return self.status == PaymentStatus.FAILED
    
    @property
    def is_refunded(self) -> bool:
        """Check if payment is fully refunded."""
        return self.status == PaymentStatus.REFUNDED
    
    @property
    def is_partially_refunded(self) -> bool:
        """Check if payment is partially refunded."""
        return self.status == PaymentStatus.PARTIALLY_REFUNDED
    
    @property
    def is_authorized(self) -> bool:
        """Check if payment is authorized but not captured."""
        return self.status == PaymentStatus.AUTHORIZED
    
    @property
    def refundable_amount(self) -> float:
        """Get the amount that can still be refunded."""
        return round(self.amount - self.refunded_amount, 2)
    
    @property
    def can_refund(self) -> bool:
        """Check if payment can be refunded."""
        return (
            self.is_successful and 
            self.refundable_amount > 0 and
            self.provider != PaymentProvider.INTERNAL
        )
    
    @property
    def requires_action(self) -> bool:
        """Check if payment requires user action (3D Secure, etc.)."""
        return (
            self.status == PaymentStatus.PENDING and
            self.metadata.get('requires_action', False)
        )
    
    @property
    def action_url(self) -> Optional[str]:
        """Get URL for payment action if required."""
        return self.metadata.get('action_url') if self.requires_action else None
    
    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction ID.
        
        Returns:
            Unique transaction ID string
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4().hex)[:8].upper()
        return f"TXN{timestamp}{unique_id}"
    
    def _generate_invoice_number(self) -> str:
        """Generate a unique invoice number.
        
        Returns:
            Unique invoice number
        """
        timestamp = datetime.utcnow().strftime('%Y%m')
        unique_id = str(uuid.uuid4().hex)[:6].upper()
        return f"INV-{timestamp}-{unique_id}"
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate the payment data.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate amount
        if self.amount <= 0:
            errors.append("Amount must be greater than 0")
        elif self.amount > 1000000:  # $1M max
            errors.append("Amount exceeds maximum allowed")
        
        # Validate refunded amount
        if self.refunded_amount < 0:
            errors.append("Refunded amount cannot be negative")
        elif self.refunded_amount > self.amount:
            errors.append("Refunded amount cannot exceed payment amount")
        
        # Validate card info if applicable
        if self.payment_method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
            if self.card_last_four and not self.card_last_four.isdigit():
                errors.append("Card last four must be digits")
            if self.card_last_four and len(self.card_last_four) != 4:
                errors.append("Card last four must be exactly 4 digits")
        
        # Validate billing address if provided
        if self.billing_address:
            required_fields = ['line1', 'city', 'country']
            for field in required_fields:
                if field not in self.billing_address:
                    errors.append(f"Billing address missing required field: {field}")
        
        return len(errors) == 0, errors
    
    def process_success(self, provider_response: Dict[str, Any]) -> None:
        """Mark payment as successful.
        
        Args:
            provider_response: Response from payment provider
        """
        self.status = PaymentStatus.PAID
        self.payment_date = datetime.utcnow()
        self.provider_response = provider_response
        self.error_message = None
        self.updated_at = datetime.utcnow()
        
        # Update transaction ID if provided
        if 'transaction_id' in provider_response:
            self.transaction_id = provider_response['transaction_id']
    
    def process_failure(self, error_message: str, provider_response: Optional[Dict[str, Any]] = None) -> None:
        """Mark payment as failed.
        
        Args:
            error_message: Error message describing the failure
            provider_response: Optional provider response
        """
        self.status = PaymentStatus.FAILED
        self.error_message = error_message
        if provider_response:
            self.provider_response = provider_response
        self.updated_at = datetime.utcnow()
    
    def process_refund(self, amount: float, reason: Optional[str] = None) -> bool:
        """Process a refund for this payment.
        
        Args:
            amount: Amount to refund
            reason: Reason for refund
            
        Returns:
            True if refund was processed, False otherwise
        """
        if not self.can_refund:
            return False
        
        if amount > self.refundable_amount:
            return False
        
        # Update refunded amount
        self.refunded_amount = round(self.refunded_amount + amount, 2)
        self.refund_reason = reason or self.refund_reason
        
        # Update status based on refund amount
        if abs(self.refunded_amount - self.amount) < 0.01:  # Within rounding error
            self.status = PaymentStatus.REFUNDED
        else:
            self.status = PaymentStatus.PARTIALLY_REFUNDED
        
        self.updated_at = datetime.utcnow()
        
        # Add refund to metadata
        if 'refunds' not in self.metadata:
            self.metadata['refunds'] = []
        
        self.metadata['refunds'].append({
            'amount': amount,
            'reason': reason,
            'date': datetime.utcnow().isoformat()
        })
        
        return True
    
    def authorize(self) -> None:
        """Authorize the payment without capturing."""
        if self.status == PaymentStatus.PENDING:
            self.status = PaymentStatus.AUTHORIZED
            self.updated_at = datetime.utcnow()
    
    def capture(self) -> bool:
        """Capture an authorized payment.
        
        Returns:
            True if capture successful, False otherwise
        """
        if self.status == PaymentStatus.AUTHORIZED:
            self.status = PaymentStatus.PAID
            self.payment_date = datetime.utcnow()
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def void(self) -> bool:
        """Void an authorized payment.
        
        Returns:
            True if void successful, False otherwise
        """
        if self.status == PaymentStatus.AUTHORIZED:
            self.status = PaymentStatus.REFUNDED
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def generate_receipt(self) -> Dict[str, Any]:
        """Generate a receipt for the payment.
        
        Returns:
            Dictionary with receipt data
        """
        return {
            'receipt_number': self.invoice_number,
            'date': self.payment_date.isoformat() if self.payment_date else None,
            'amount': self.amount,
            'currency': self.currency.value,
            'status': self.status.value,
            'payment_method': self.payment_method.value,
            'transaction_id': self.transaction_id,
            'reservation_id': self.reservation_id,
            'billing_address': self.billing_address,
            'card_details': {
                'brand': self.card_brand,
                'last_four': self.card_last_four
            } if self.card_brand or self.card_last_four else None
        }
    
    def calculate_fee(self, fee_percentage: float = 2.9, fixed_fee: float = 0.30) -> float:
        """Calculate processing fee for the payment.
        
        Args:
            fee_percentage: Percentage fee (e.g., 2.9 for 2.9%)
            fixed_fee: Fixed fee amount
            
        Returns:
            Calculated fee amount
        """
        percentage_fee = (self.amount * fee_percentage) / 100
        return round(percentage_fee + fixed_fee, 2)
    
    def calculate_net_amount(self, fee_percentage: float = 2.9, fixed_fee: float = 0.30) -> float:
        """Calculate net amount after fees.
        
        Args:
            fee_percentage: Percentage fee
            fixed_fee: Fixed fee amount
            
        Returns:
            Net amount after fees
        """
        fee = self.calculate_fee(fee_percentage, fixed_fee)
        return round(self.amount - fee, 2)
    
    def verify_signature(self, payload: str, signature: str, secret_key: str) -> bool:
        """Verify webhook signature from payment provider.
        
        Args:
            payload: Raw payload string
            signature: Signature to verify
            secret_key: Secret key for verification
            
        Returns:
            True if signature is valid, False otherwise
        """
        expected = hmac.new(
            secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert payment to dictionary.
        
        Args:
            include_sensitive: Whether to include sensitive data
            
        Returns:
            Dictionary representation of the payment
        """
        result = {
            "payment_id": self.payment_id,
            "reservation_id": self.reservation_id,
            "user_id": self.user_id,
            "amount": self.amount,
            "currency": self.currency.value if self.currency else None,
            "status": self.status.value if self.status else None,
            "status_display": self.status.name.replace('_', ' ').title() if self.status else None,
            "payment_method": self.payment_method.value if self.payment_method else None,
            "payment_type": self.payment_type.value if self.payment_type else None,
            "provider": self.provider.value if self.provider else None,
            "transaction_id": self.transaction_id,
            "refunded_amount": self.refunded_amount,
            "refund_reason": self.refund_reason,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "receipt_url": self.receipt_url,
            "invoice_number": self.invoice_number,
            "is_successful": self.is_successful,
            "is_refunded": self.is_refunded,
            "is_partially_refunded": self.is_partially_refunded,
            "refundable_amount": self.refundable_amount,
            "can_refund": self.can_refund,
            "requires_action": self.requires_action,
            "action_url": self.action_url,
        }
        
        # Include billing address (not sensitive)
        if self.billing_address:
            result["billing_address"] = self.billing_address
        
        # Include non-sensitive card info
        if self.card_brand:
            result["card_brand"] = self.card_brand
        
        # Include sensitive data only if requested
        if include_sensitive:
            result["card_last_four"] = self.card_last_four
            result["provider_response"] = self.provider_response
            result["error_message"] = self.error_message
            result["metadata"] = self.metadata
        
        return result
    
    def to_dict_minimal(self) -> Dict[str, Any]:
        """Convert payment to minimal dictionary (for list views).
        
        Returns:
            Minimal dictionary representation of the payment
        """
        return {
            "payment_id": self.payment_id,
            "invoice_number": self.invoice_number,
            "amount": self.amount,
            "currency": self.currency.value if self.currency else None,
            "status": self.status.value if self.status else None,
            "payment_method": self.payment_method.value if self.payment_method else None,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "is_successful": self.is_successful,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Payment':
        """Create payment from dictionary.
        
        Args:
            data: Dictionary containing payment data
            
        Returns:
            New Payment instance
        """
        # Handle enums
        currency = data.get('currency')
        if currency and isinstance(currency, str):
            try:
                currency = Currency(currency)
            except ValueError:
                currency = Currency.USD
        
        status = data.get('status')
        if status and isinstance(status, str):
            try:
                status = PaymentStatus(status)
            except ValueError:
                try:
                    status = PaymentStatus[status.upper()]
                except KeyError:
                    status = PaymentStatus.PENDING
        
        payment_method = data.get('payment_method')
        if payment_method and isinstance(payment_method, str):
            try:
                payment_method = PaymentMethod(payment_method)
            except ValueError:
                try:
                    payment_method = PaymentMethod[payment_method.upper()]
                except KeyError:
                    payment_method = PaymentMethod.CREDIT_CARD
        
        payment_type = data.get('payment_type')
        if payment_type and isinstance(payment_type, str):
            try:
                payment_type = PaymentType(payment_type)
            except ValueError:
                try:
                    payment_type = PaymentType[payment_type.upper()]
                except KeyError:
                    payment_type = PaymentType.RESERVATION
        
        provider = data.get('provider')
        if provider and isinstance(provider, str):
            try:
                provider = PaymentProvider(provider)
            except ValueError:
                try:
                    provider = PaymentProvider[provider.upper()]
                except KeyError:
                    provider = PaymentProvider.INTERNAL
        
        # Parse datetime fields
        payment_date = data.get('payment_date')
        if payment_date and isinstance(payment_date, str):
            try:
                payment_date = datetime.fromisoformat(payment_date.replace('Z', '+00:00'))
            except ValueError:
                payment_date = None
        
        created_at = data.get('created_at')
        if created_at and isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = None
        
        updated_at = data.get('updated_at')
        if updated_at and isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except ValueError:
                updated_at = None
        
        return cls(
            payment_id=data.get('payment_id'),
            reservation_id=data.get('reservation_id'),
            user_id=data.get('user_id', 0),
            amount=data.get('amount', 0.0),
            currency=currency,
            status=status,
            payment_method=payment_method,
            payment_type=payment_type,
            provider=provider,
            transaction_id=data.get('transaction_id'),
            provider_response=data.get('provider_response'),
            error_message=data.get('error_message'),
            refunded_amount=data.get('refunded_amount', 0.0),
            refund_reason=data.get('refund_reason'),
            payment_date=payment_date,
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get('metadata'),
            receipt_url=data.get('receipt_url'),
            invoice_number=data.get('invoice_number'),
            billing_address=data.get('billing_address'),
            card_last_four=data.get('card_last_four'),
            card_brand=data.get('card_brand'),
        )
    
    @classmethod
    def get_payment_methods(cls) -> List[Dict[str, str]]:
        """Get list of available payment methods.
        
        Returns:
            List of dictionaries with value and display name
        """
        return [
            {"value": pm.value, "display": pm.name.replace('_', ' ').title()}
            for pm in PaymentMethod
        ]
    
    @classmethod
    def get_payment_providers(cls) -> List[Dict[str, str]]:
        """Get list of available payment providers.
        
        Returns:
            List of dictionaries with value and display name
        """
        return [
            {"value": pp.value, "display": pp.name.replace('_', ' ').title()}
            for pp in PaymentProvider
        ]
    
    @classmethod
    def get_currencies(cls) -> List[Dict[str, str]]:
        """Get list of supported currencies.
        
        Returns:
            List of dictionaries with code and display name
        """
        return [
            {"code": c.value, "display": c.name}
            for c in Currency
        ]
    
    def __eq__(self, other: object) -> bool:
        """Check equality with another payment."""
        if not isinstance(other, Payment):
            return False
        return (
            self.payment_id is not None and 
            other.payment_id is not None and 
            self.payment_id == other.payment_id
        )
    
    def __hash__(self) -> int:
        """Hash based on payment_id."""
        return hash(self.payment_id) if self.payment_id else id(self)