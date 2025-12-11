# File: src/infrastructure/messaging.py
"""
Messaging Infrastructure for Parking Management System

This module implements messaging patterns for event-driven communication:
1. Event Bus - For intra-process event publishing/subscription
2. Message Queue - For inter-process asynchronous messaging
3. Event Store - For storing domain events for event sourcing
4. Message Brokers - Integration with external brokers (RabbitMQ, Kafka, Redis)
5. Event Handlers - For processing domain events asynchronously

Key Patterns:
- Publish/Subscribe
- Command/Query Responsibility Segregation (CQRS)
- Event Sourcing
- Outbox Pattern for reliable messaging
- Retry mechanisms and dead letter queues

Supported Brokers:
- Redis Pub/Sub
- RabbitMQ
- Apache Kafka
- In-memory (for testing)
"""

from abc import ABC, abstractmethod
from typing import (
    Type, TypeVar, Generic, Optional, Dict, List, Any,
    Union, Callable, Tuple, Set, Coroutine, Awaitable
)
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json
import asyncio
from dataclasses import dataclass, asdict, field
from enum import Enum
from uuid import UUID, uuid4
import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from contextlib import contextmanager

import redis
import pika
from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import KafkaError
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient

from ..domain.models import (
    Vehicle, ParkingSlot, ParkingLot, Customer, Invoice, Payment, Reservation,
    VehicleType, SlotType, ChargerType
)
from ..application.dtos import (
    VehicleDTO, ParkingSlotDTO, ParkingLotDTO, CustomerDTO,
    InvoiceDTO, PaymentDTO, ReservationDTO
)


# ============================================================================
# MESSAGE TYPES AND ENUMS
# ============================================================================

class MessageType(str, Enum):
    """Types of messages in the system"""
    DOMAIN_EVENT = "domain_event"
    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ALERT = "alert"


class EventType(str, Enum):
    """Domain event types"""
    # Vehicle events
    VEHICLE_REGISTERED = "vehicle_registered"
    VEHICLE_UPDATED = "vehicle_updated"
    VEHICLE_DELETED = "vehicle_deleted"
    
    # Parking events
    PARKING_SLOT_CREATED = "parking_slot_created"
    PARKING_SLOT_OCCUPIED = "parking_slot_occupied"
    PARKING_SLOT_RELEASED = "parking_slot_released"
    PARKING_SLOT_RESERVED = "parking_slot_reserved"
    
    # Parking lot events
    PARKING_LOT_CREATED = "parking_lot_created"
    PARKING_LOT_UPDATED = "parking_lot_updated"
    PARKING_LOT_STATUS_CHANGED = "parking_lot_status_changed"
    
    # Customer events
    CUSTOMER_REGISTERED = "customer_registered"
    CUSTOMER_UPDATED = "customer_updated"
    
    # Billing events
    INVOICE_CREATED = "invoice_created"
    INVOICE_PAID = "invoice_paid"
    PAYMENT_PROCESSED = "payment_processed"
    
    # Charging events
    CHARGING_SESSION_STARTED = "charging_session_started"
    CHARGING_SESSION_STOPPED = "charging_session_stopped"
    
    # Reservation events
    RESERVATION_CREATED = "reservation_created"
    RESERVATION_CANCELLED = "reservation_cancelled"
    RESERVATION_CONFIRMED = "reservation_confirmed"
    
    # System events
    SYSTEM_ALERT = "system_alert"
    MAINTENANCE_REQUIRED = "maintenance_required"


class CommandType(str, Enum):
    """Command types"""
    PARK_VEHICLE = "park_vehicle"
    EXIT_VEHICLE = "exit_vehicle"
    START_CHARGING = "start_charging"
    STOP_CHARGING = "stop_charging"
    CREATE_RESERVATION = "create_reservation"
    CANCEL_RESERVATION = "cancel_reservation"
    PROCESS_PAYMENT = "process_payment"
    UPDATE_PRICING = "update_pricing"


# ============================================================================
# MESSAGE BASE CLASSES
# ============================================================================

@dataclass
class Message:
    """Base message class"""
    message_id: UUID = field(default_factory=uuid4)
    message_type: MessageType = MessageType.DOMAIN_EVENT
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[UUID] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['message_id'] = UUID(data['message_id'])
        if data.get('correlation_id'):
            data['correlation_id'] = UUID(data['correlation_id'])
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create message from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class DomainEvent(Message):
    """Domain event message"""
    event_type: EventType = EventType.SYSTEM_ALERT
    aggregate_id: Optional[UUID] = None
    aggregate_type: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    
    def __post_init__(self):
        self.message_type = MessageType.DOMAIN_EVENT


@dataclass
class Command(Message):
    """Command message"""
    command_type: CommandType = CommandType.PARK_VEHICLE
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.message_type = MessageType.COMMAND


@dataclass
class Query(Message):
    """Query message"""
    query_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.message_type = MessageType.QUERY


@dataclass
class Response(Message):
    """Response message"""
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        self.message_type = MessageType.RESPONSE


@dataclass
class Notification(Message):
    """Notification message"""
    notification_type: str = ""
    recipient: Optional[str] = None
    title: str = ""
    body: str = ""
    priority: str = "normal"  # low, normal, high, urgent
    
    def __post_init__(self):
        self.message_type = MessageType.NOTIFICATION


@dataclass
class Alert(Message):
    """Alert message"""
    alert_type: str = ""
    severity: str = "info"  # info, warning, critical
    metric: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None
    message: str = ""
    
    def __post_init__(self):
        self.message_type = MessageType.ALERT


# ============================================================================
# EVENT HANDLERS
# ============================================================================

class EventHandler(ABC):
    """Abstract base class for event handlers"""
    
    @abstractmethod
    def handle(self, event: DomainEvent) -> None:
        """Handle a domain event"""
        pass
    
    def can_handle(self, event: DomainEvent) -> bool:
        """Check if this handler can handle the event"""
        return True


class AsyncEventHandler(ABC):
    """Abstract base class for async event handlers"""
    
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Handle a domain event asynchronously"""
        pass
    
    def can_handle(self, event: DomainEvent) -> bool:
        """Check if this handler can handle the event"""
        return True


# ============================================================================
# EVENT BUS (In-memory)
# ============================================================================

class EventBus:
    """
    In-memory event bus for intra-process event publishing
    
    Implements publish/subscribe pattern within the same process.
    Useful for domain events that need to trigger side effects.
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[EventHandler]] = {}
        self._async_subscribers: Dict[EventType, List[AsyncEventHandler]] = {}
        self._logger = logging.getLogger(self.__class__.__name__)
        
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe to events of a specific type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            self._logger.debug(f"Subscribed {handler.__class__.__name__} to {event_type}")
    
    def subscribe_async(self, event_type: EventType, handler: AsyncEventHandler) -> None:
        """Subscribe async handler to events of a specific type"""
        if event_type not in self._async_subscribers:
            self._async_subscribers[event_type] = []
        
        if handler not in self._async_subscribers[event_type]:
            self._async_subscribers[event_type].append(handler)
            self._logger.debug(f"Subscribed async {handler.__class__.__name__} to {event_type}")
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe handler from events"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                self._logger.debug(f"Unsubscribed {handler.__class__.__name__} from {event_type}")
            except ValueError:
                pass
    
    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribers"""
        self._logger.info(f"Publishing event: {event.event_type} (ID: {event.message_id})")
        
        # Publish to synchronous handlers
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            if handler.can_handle(event):
                try:
                    handler.handle(event)
                    self._logger.debug(f"Event handled by {handler.__class__.__name__}")
                except Exception as e:
                    self._logger.error(f"Error handling event {event.event_type} with {handler.__class__.__name__}: {e}")
        
        # Publish to async handlers (fire and forget)
        async_handlers = self._async_subscribers.get(event.event_type, [])
        if async_handlers:
            # Run async handlers in background
            asyncio.create_task(self._publish_async(event, async_handlers))
    
    async def publish_async(self, event: DomainEvent) -> None:
        """Publish an event asynchronously"""
        self._logger.info(f"Publishing event async: {event.event_type} (ID: {event.message_id})")
        
        # Publish to async handlers
        async_handlers = self._async_subscribers.get(event.event_type, [])
        await self._publish_async(event, async_handlers)
        
        # Publish to sync handlers (run in thread pool)
        handlers = self._subscribers.get(event.event_type, [])
        if handlers:
            await asyncio.get_event_loop().run_in_executor(
                None, self._publish_sync_in_executor, event, handlers
            )
    
    async def _publish_async(self, event: DomainEvent, handlers: List[AsyncEventHandler]) -> None:
        """Publish to async handlers"""
        tasks = []
        for handler in handlers:
            if handler.can_handle(event):
                tasks.append(handler.handle(event))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for handler, result in zip(handlers, results):
                if isinstance(result, Exception):
                    self._logger.error(f"Error in async handler {handler.__class__.__name__}: {result}")
    
    def _publish_sync_in_executor(self, event: DomainEvent, handlers: List[EventHandler]) -> None:
        """Publish to sync handlers in thread pool"""
        for handler in handlers:
            if handler.can_handle(event):
                try:
                    handler.handle(event)
                except Exception as e:
                    self._logger.error(f"Error in sync handler {handler.__class__.__name__}: {e}")
    
    def clear_subscribers(self) -> None:
        """Clear all subscribers (for testing)"""
        self._subscribers.clear()
        self._async_subscribers.clear()


# ============================================================================
# MESSAGE QUEUE ABSTRACTIONS
# ============================================================================

class MessageQueue(ABC):
    """Abstract base class for message queues"""
    
    @abstractmethod
    def publish(self, topic: str, message: Message) -> bool:
        """Publish a message to a topic"""
        pass
    
    @abstractmethod
    def subscribe(self, topic: str, callback: Callable[[Message], None]) -> str:
        """Subscribe to messages from a topic"""
        pass
    
    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic"""
        pass
    
    @abstractmethod
    def create_topic(self, topic: str, **kwargs) -> bool:
        """Create a new topic"""
        pass
    
    @abstractmethod
    def delete_topic(self, topic: str) -> bool:
        """Delete a topic"""
        pass


class AsyncMessageQueue(ABC):
    """Abstract base class for async message queues"""
    
    @abstractmethod
    async def publish(self, topic: str, message: Message) -> bool:
        """Publish a message to a topic asynchronously"""
        pass
    
    @abstractmethod
    async def subscribe(self, topic: str, callback: Callable[[Message], Awaitable[None]]) -> str:
        """Subscribe to messages from a topic asynchronously"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic asynchronously"""
        pass


# ============================================================================
# REDIS MESSAGE QUEUE
# ============================================================================

class RedisMessageQueue(MessageQueue):
    """Redis-based message queue using Pub/Sub"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", **kwargs):
        self.redis_url = redis_url
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Redis connection
        self.redis_client = redis.Redis.from_url(redis_url, **kwargs)
        self.pubsub = self.redis_client.pubsub()
        
        # Subscription tracking
        self._subscriptions: Dict[str, str] = {}  # subscription_id -> topic
        self._callbacks: Dict[str, Callable[[Message], None]] = {}  # subscription_id -> callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def publish(self, topic: str, message: Message) -> bool:
        """Publish a message to a Redis channel"""
        try:
            message_json = message.to_json()
            result = self.redis_client.publish(topic, message_json)
            self._logger.debug(f"Published message to {topic}: {message.message_id}")
            return result > 0
        except Exception as e:
            self._logger.error(f"Error publishing to Redis: {e}")
            return False
    
    def subscribe(self, topic: str, callback: Callable[[Message], None]) -> str:
        """Subscribe to a Redis channel"""
        subscription_id = str(uuid4())
        
        self._subscriptions[subscription_id] = topic
        self._callbacks[subscription_id] = callback
        
        # Subscribe in Redis
        self.pubsub.subscribe(topic)
        
        # Start listener thread if not running
        if not self._running:
            self._start_listener()
        
        self._logger.debug(f"Subscribed to {topic} with ID {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a Redis channel"""
        if subscription_id not in self._subscriptions:
            return False
        
        topic = self._subscriptions[subscription_id]
        
        # Remove from tracking
        del self._subscriptions[subscription_id]
        del self._callbacks[subscription_id]
        
        # Unsubscribe from Redis if no more subscribers for this topic
        if topic not in self._subscriptions.values():
            self.pubsub.unsubscribe(topic)
            self._logger.debug(f"Unsubscribed from {topic}")
        
        return True
    
    def create_topic(self, topic: str, **kwargs) -> bool:
        """Create a Redis channel (topics are created automatically on publish)"""
        # In Redis, channels are created automatically when publishing
        self._logger.debug(f"Redis channel '{topic}' will be created on first publish")
        return True
    
    def delete_topic(self, topic: str) -> bool:
        """Delete a Redis channel (not directly supported, unsubscribe all)"""
        # Find all subscriptions for this topic
        subscriptions_to_remove = [
            sid for sid, t in self._subscriptions.items() if t == topic
        ]
        
        for sid in subscriptions_to_remove:
            self.unsubscribe(sid)
        
        self._logger.debug(f"Removed all subscriptions from topic {topic}")
        return True
    
    def _start_listener(self):
        """Start the Redis message listener in a separate thread"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        self._logger.info("Started Redis message listener")
    
    def _listen(self):
        """Listen for Redis messages"""
        while self._running:
            try:
                message = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    self._handle_message(message)
            except Exception as e:
                self._logger.error(f"Error in Redis listener: {e}")
                time.sleep(1)  # Avoid tight loop on error
    
    def _handle_message(self, redis_message: Dict[str, Any]):
        """Handle incoming Redis message"""
        try:
            topic = redis_message['channel'].decode('utf-8')
            data = redis_message['data'].decode('utf-8')
            
            # Parse message
            message_dict = json.loads(data)
            message = Message.from_dict(message_dict)
            
            # Find callbacks for this topic
            for subscription_id, callback_topic in self._subscriptions.items():
                if callback_topic == topic:
                    callback = self._callbacks[subscription_id]
                    try:
                        callback(message)
                    except Exception as e:
                        self._logger.error(f"Error in callback for subscription {subscription_id}: {e}")
                        
        except Exception as e:
            self._logger.error(f"Error handling Redis message: {e}")
    
    def close(self):
        """Close Redis connections"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        
        self.pubsub.close()
        self.redis_client.close()
        self._logger.info("Redis message queue closed")


# ============================================================================
# RABBITMQ MESSAGE QUEUE
# ============================================================================

class RabbitMQMessageQueue(MessageQueue):
    """RabbitMQ-based message queue"""
    
    def __init__(self, amqp_url: str = "amqp://localhost:5672", **kwargs):
        self.amqp_url = amqp_url
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Connection parameters
        self.connection_params = pika.URLParameters(amqp_url)
        
        # Connection and channel (lazy initialization)
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None
        
        # Subscription tracking
        self._consumer_tags: Dict[str, str] = {}  # subscription_id -> consumer_tag
        self._callbacks: Dict[str, Callable[[Message], None]] = {}  # subscription_id -> callback
    
    def _ensure_connection(self) -> None:
        """Ensure RabbitMQ connection is established"""
        if not self._connection or self._connection.is_closed:
            self._connection = pika.BlockingConnection(self.connection_params)
            self._channel = self._connection.channel()
            self._logger.debug("RabbitMQ connection established")
    
    def publish(self, topic: str, message: Message) -> bool:
        """Publish a message to a RabbitMQ exchange"""
        try:
            self._ensure_connection()
            
            # Declare exchange
            self._channel.exchange_declare(
                exchange=topic,
                exchange_type='topic',
                durable=True
            )
            
            # Publish message
            message_json = message.to_json()
            self._channel.basic_publish(
                exchange=topic,
                routing_key=message.event_type if isinstance(message, DomainEvent) else '',
                body=message_json.encode('utf-8'),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json',
                    message_id=str(message.message_id),
                    timestamp=int(message.timestamp.timestamp()),
                    correlation_id=str(message.correlation_id) if message.correlation_id else None
                )
            )
            
            self._logger.debug(f"Published message to {topic}: {message.message_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error publishing to RabbitMQ: {e}")
            return False
    
    def subscribe(self, topic: str, callback: Callable[[Message], None]) -> str:
        """Subscribe to a RabbitMQ queue"""
        try:
            self._ensure_connection()
            
            # Declare exchange
            self._channel.exchange_declare(
                exchange=topic,
                exchange_type='topic',
                durable=True
            )
            
            # Create a unique queue for this subscriber
            subscription_id = str(uuid4())
            queue_name = f"{topic}.{subscription_id}"
            
            # Declare queue
            self._channel.queue_declare(
                queue=queue_name,
                durable=True,
                exclusive=False,
                auto_delete=True  # Delete when no consumers
            )
            
            # Bind queue to exchange with wildcard routing key
            self._channel.queue_bind(
                exchange=topic,
                queue=queue_name,
                routing_key='#'  # Receive all messages
            )
            
            # Define message handler
            def message_handler(ch, method, properties, body):
                try:
                    message_dict = json.loads(body.decode('utf-8'))
                    message = Message.from_dict(message_dict)
                    callback(message)
                except Exception as e:
                    self._logger.error(f"Error processing RabbitMQ message: {e}")
                finally:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
            
            # Start consuming
            consumer_tag = self._channel.basic_consume(
                queue=queue_name,
                on_message_callback=message_handler,
                auto_ack=False
            )
            
            # Store subscription info
            self._consumer_tags[subscription_id] = consumer_tag
            self._callbacks[subscription_id] = callback
            
            self._logger.debug(f"Subscribed to {topic} with queue {queue_name}")
            return subscription_id
            
        except Exception as e:
            self._logger.error(f"Error subscribing to RabbitMQ: {e}")
            raise
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from RabbitMQ"""
        if subscription_id not in self._consumer_tags:
            return False
        
        try:
            self._ensure_connection()
            
            consumer_tag = self._consumer_tags[subscription_id]
            self._channel.basic_cancel(consumer_tag)
            
            # Remove from tracking
            del self._consumer_tags[subscription_id]
            del self._callbacks[subscription_id]
            
            self._logger.debug(f"Unsubscribed {subscription_id}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error unsubscribing from RabbitMQ: {e}")
            return False
    
    def create_topic(self, topic: str, **kwargs) -> bool:
        """Create a RabbitMQ exchange"""
        try:
            self._ensure_connection()
            
            exchange_type = kwargs.get('exchange_type', 'topic')
            durable = kwargs.get('durable', True)
            
            self._channel.exchange_declare(
                exchange=topic,
                exchange_type=exchange_type,
                durable=durable
            )
            
            self._logger.debug(f"Created RabbitMQ exchange: {topic}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error creating RabbitMQ exchange: {e}")
            return False
    
    def delete_topic(self, topic: str) -> bool:
        """Delete a RabbitMQ exchange"""
        try:
            self._ensure_connection()
            self._channel.exchange_delete(exchange=topic)
            self._logger.debug(f"Deleted RabbitMQ exchange: {topic}")
            return True
        except Exception as e:
            self._logger.error(f"Error deleting RabbitMQ exchange: {e}")
            return False
    
    def start_consuming(self) -> None:
        """Start consuming messages (blocks)"""
        try:
            self._ensure_connection()
            self._logger.info("Starting RabbitMQ consumer...")
            self._channel.start_consuming()
        except KeyboardInterrupt:
            self._logger.info("RabbitMQ consumer stopped by user")
        except Exception as e:
            self._logger.error(f"Error in RabbitMQ consumer: {e}")
    
    def close(self):
        """Close RabbitMQ connections"""
        try:
            if self._connection and self._connection.is_open:
                self._connection.close()
                self._logger.info("RabbitMQ connection closed")
        except Exception as e:
            self._logger.error(f"Error closing RabbitMQ connection: {e}")


# ============================================================================
# KAFKA MESSAGE QUEUE
# ============================================================================

class KafkaMessageQueue(MessageQueue):
    """Kafka-based message queue"""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092", **kwargs):
        self.bootstrap_servers = bootstrap_servers
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Producer configuration
        producer_config = {
            'bootstrap_servers': bootstrap_servers,
            'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
            'key_serializer': lambda k: str(k).encode('utf-8') if k else None,
            **kwargs.get('producer_config', {})
        }
        
        # Consumer configuration
        self.consumer_config = {
            'bootstrap_servers': bootstrap_servers,
            'group_id': kwargs.get('group_id', 'parking-management'),
            'enable_auto_commit': kwargs.get('enable_auto_commit', True),
            'auto_offset_reset': kwargs.get('auto_offset_reset', 'earliest'),
            **kwargs.get('consumer_config', {})
        }
        
        # Initialize producer
        self.producer = KafkaProducer(**producer_config)
        
        # Consumer tracking
        self._consumers: Dict[str, KafkaConsumer] = {}  # subscription_id -> consumer
        self._callbacks: Dict[str, Callable[[Message], None]] = {}  # subscription_id -> callback
        self._consumer_threads: Dict[str, threading.Thread] = {}  # subscription_id -> thread
    
    def publish(self, topic: str, message: Message) -> bool:
        """Publish a message to a Kafka topic"""
        try:
            # Convert message to dict
            message_dict = message.to_dict()
            
            # Determine key (use aggregate_id for events, message_id for others)
            if isinstance(message, DomainEvent) and message.aggregate_id:
                key = str(message.aggregate_id)
            else:
                key = str(message.message_id)
            
            # Send to Kafka
            future = self.producer.send(
                topic=topic,
                key=key,
                value=message_dict
            )
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            
            self._logger.debug(
                f"Published message to {topic} partition {record_metadata.partition}, "
                f"offset {record_metadata.offset}: {message.message_id}"
            )
            return True
            
        except KafkaError as e:
            self._logger.error(f"Kafka error publishing message: {e}")
            return False
        except Exception as e:
            self._logger.error(f"Error publishing to Kafka: {e}")
            return False
    
    def subscribe(self, topic: str, callback: Callable[[Message], None]) -> str:
        """Subscribe to a Kafka topic"""
        subscription_id = str(uuid4())
        
        try:
            # Create consumer
            consumer = KafkaConsumer(
                topic,
                **self.consumer_config
            )
            
            # Store consumer and callback
            self._consumers[subscription_id] = consumer
            self._callbacks[subscription_id] = callback
            
            # Start consumer thread
            thread = threading.Thread(
                target=self._consume_messages,
                args=(subscription_id,),
                daemon=True
            )
            self._consumer_threads[subscription_id] = thread
            thread.start()
            
            self._logger.debug(f"Subscribed to Kafka topic {topic} with ID {subscription_id}")
            return subscription_id
            
        except Exception as e:
            self._logger.error(f"Error subscribing to Kafka: {e}")
            raise
    
    def _consume_messages(self, subscription_id: str):
        """Consume messages from Kafka in a separate thread"""
        consumer = self._consumers.get(subscription_id)
        callback = self._callbacks.get(subscription_id)
        
        if not consumer or not callback:
            return
        
        try:
            for kafka_message in consumer:
                try:
                    # Parse message
                    message_dict = json.loads(kafka_message.value.decode('utf-8'))
                    message = Message.from_dict(message_dict)
                    
                    # Call callback
                    callback(message)
                    
                except Exception as e:
                    self._logger.error(f"Error processing Kafka message: {e}")
                    
        except Exception as e:
            self._logger.error(f"Error in Kafka consumer for {subscription_id}: {e}")
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from Kafka topic"""
        if subscription_id not in self._consumers:
            return False
        
        try:
            # Stop consumer
            consumer = self._consumers[subscription_id]
            consumer.close()
            
            # Stop thread
            thread = self._consumer_threads.get(subscription_id)
            if thread:
                thread.join(timeout=5.0)
            
            # Remove from tracking
            del self._consumers[subscription_id]
            del self._callbacks[subscription_id]
            if subscription_id in self._consumer_threads:
                del self._consumer_threads[subscription_id]
            
            self._logger.debug(f"Unsubscribed {subscription_id} from Kafka")
            return True
            
        except Exception as e:
            self._logger.error(f"Error unsubscribing from Kafka: {e}")
            return False
    
    def create_topic(self, topic: str, **kwargs) -> bool:
        """Create a Kafka topic"""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers
            )
            
            num_partitions = kwargs.get('num_partitions', 1)
            replication_factor = kwargs.get('replication_factor', 1)
            
            topic_list = [NewTopic(
                name=topic,
                num_partitions=num_partitions,
                replication_factor=replication_factor
            )]
            
            admin_client.create_topics(new_topics=topic_list)
            admin_client.close()
            
            self._logger.debug(f"Created Kafka topic: {topic}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error creating Kafka topic: {e}")
            return False
    
    def delete_topic(self, topic: str) -> bool:
        """Delete a Kafka topic"""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers
            )
            
            admin_client.delete_topics([topic])
            admin_client.close()
            
            self._logger.debug(f"Deleted Kafka topic: {topic}")
            return True
            
        except Exception as e:
            self._logger.error(f"Error deleting Kafka topic: {e}")
            return False
    
    def close(self):
        """Close Kafka connections"""
        try:
            # Close all consumers
            for subscription_id in list(self._consumers.keys()):
                self.unsubscribe(subscription_id)
            
            # Close producer
            self.producer.close()
            
            self._logger.info("Kafka connections closed")
            
        except Exception as e:
            self._logger.error(f"Error closing Kafka connections: {e}")


# ============================================================================
# EVENT STORE
# ============================================================================

class EventStore:
    """
    Event store for event sourcing
    
    Stores all domain events for aggregates, enabling:
    - Event sourcing
    - Audit logging
    - Replay of events
    - Temporal queries
    """
    
    def __init__(self, mongo_url: str = "mongodb://localhost:27017", **kwargs):
        self.mongo_url = mongo_url
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # MongoDB client
        self.client = pymongo.MongoClient(mongo_url, **kwargs)
        self.db = self.client['event_store']
        self.events_collection = self.db['events']
        
        # Create indexes
        self.events_collection.create_index([('aggregate_id', 1), ('version', 1)], unique=True)
        self.events_collection.create_index([('event_type', 1)])
        self.events_collection.create_index([('timestamp', 1)])
        self.events_collection.create_index([('aggregate_type', 1)])
    
    def save(self, event: DomainEvent) -> bool:
        """Save a domain event to the store"""
        try:
            # Convert event to document
            event_doc = self._event_to_document(event)
            
            # Insert into MongoDB
            result = self.events_collection.insert_one(event_doc)
            
            self._logger.debug(f"Saved event {event.event_type} for aggregate {event.aggregate_id}")
            return result.acknowledged
            
        except Exception as e:
            self._logger.error(f"Error saving event to store: {e}")
            return False
    
    def save_batch(self, events: List[DomainEvent]) -> bool:
        """Save multiple events in a batch"""
        try:
            event_docs = [self._event_to_document(event) for event in events]
            
            result = self.events_collection.insert_many(event_docs)
            
            self._logger.debug(f"Saved {len(events)} events in batch")
            return result.acknowledged
            
        except Exception as e:
            self._logger.error(f"Error saving batch to event store: {e}")
            return False
    
    def get_events_for_aggregate(self, aggregate_id: UUID, from_version: int = 0) -> List[DomainEvent]:
        """Get all events for a specific aggregate"""
        try:
            query = {
                'aggregate_id': str(aggregate_id),
                'version': {'$gte': from_version}
            }
            
            cursor = self.events_collection.find(query).sort('version', 1)
            events = [self._document_to_event(doc) for doc in cursor]
            
            return events
            
        except Exception as e:
            self._logger.error(f"Error getting events for aggregate: {e}")
            return []
    
    def get_events_by_type(self, event_type: EventType, limit: int = 100) -> List[DomainEvent]:
        """Get events by type"""
        try:
            cursor = self.events_collection.find(
                {'event_type': event_type.value}
            ).sort('timestamp', -1).limit(limit)
            
            events = [self._document_to_event(doc) for doc in cursor]
            return events
            
        except Exception as e:
            self._logger.error(f"Error getting events by type: {e}")
            return []
    
    def get_events_since(self, timestamp: datetime, limit: int = 100) -> List[DomainEvent]:
        """Get events since a specific timestamp"""
        try:
            cursor = self.events_collection.find(
                {'timestamp': {'$gte': timestamp}}
            ).sort('timestamp', 1).limit(limit)
            
            events = [self._document_to_event(doc) for doc in cursor]
            return events
            
        except Exception as e:
            self._logger.error(f"Error getting events since timestamp: {e}")
            return []
    
    def get_aggregate_ids(self, aggregate_type: Optional[str] = None) -> List[UUID]:
        """Get all aggregate IDs (optionally filtered by type)"""
        try:
            query = {}
            if aggregate_type:
                query['aggregate_type'] = aggregate_type
            
            cursor = self.events_collection.distinct('aggregate_id', query)
            return [UUID(agg_id) for agg_id in cursor]
            
        except Exception as e:
            self._logger.error(f"Error getting aggregate IDs: {e}")
            return []
    
    def get_last_event_for_aggregate(self, aggregate_id: UUID) -> Optional[DomainEvent]:
        """Get the last event for an aggregate"""
        try:
            doc = self.events_collection.find_one(
                {'aggregate_id': str(aggregate_id)},
                sort=[('version', -1)]
            )
            
            if doc:
                return self._document_to_event(doc)
            return None
            
        except Exception as e:
            self._logger.error(f"Error getting last event for aggregate: {e}")
            return None
    
    def _event_to_document(self, event: DomainEvent) -> Dict[str, Any]:
        """Convert DomainEvent to MongoDB document"""
        return {
            '_id': str(event.message_id),
            'message_id': str(event.message_id),
            'event_type': event.event_type.value,
            'timestamp': event.timestamp,
            'aggregate_id': str(event.aggregate_id) if event.aggregate_id else None,
            'aggregate_type': event.aggregate_type,
            'version': event.version,
            'data': event.data,
            'metadata': event.metadata,
            'correlation_id': str(event.correlation_id) if event.correlation_id else None,
            'source': event.source
        }
    
    def _document_to_event(self, doc: Dict[str, Any]) -> DomainEvent:
        """Convert MongoDB document to DomainEvent"""
        return DomainEvent(
            message_id=UUID(doc['message_id']),
            event_type=EventType(doc['event_type']),
            timestamp=doc['timestamp'],
            aggregate_id=UUID(doc['aggregate_id']) if doc.get('aggregate_id') else None,
            aggregate_type=doc.get('aggregate_type'),
            version=doc.get('version', 1),
            data=doc.get('data', {}),
            metadata=doc.get('metadata', {}),
            correlation_id=UUID(doc['correlation_id']) if doc.get('correlation_id') else None,
            source=doc.get('source')
        )
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()
        self._logger.info("Event store closed")


# ============================================================================
# MESSAGE BUS (Orchestrator)
# ============================================================================

class MessageBus:
    """
    Orchestrates message flow between different messaging components
    
    Routes messages between event bus, message queues, and event store.
    Implements the outbox pattern for reliable messaging.
    """
    
    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        message_queue: Optional[MessageQueue] = None,
        event_store: Optional[EventStore] = None
    ):
        self.event_bus = event_bus or EventBus()
        self.message_queue = message_queue
        self.event_store = event_store
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Outbox for reliable messaging
        self._outbox: List[Tuple[str, Message]] = []
        self._outbox_lock = threading.Lock()
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
    
    def publish_event(self, event: DomainEvent, store: bool = True) -> None:
        """Publish a domain event through all channels"""
        self._logger.info(f"Publishing event {event.event_type} (ID: {event.message_id})")
        
        # Store event if event store is available
        if store and self.event_store:
            try:
                self.event_store.save(event)
            except Exception as e:
                self._logger.error(f"Failed to save event to store: {e}")
        
        # Publish to in-memory event bus
        try:
            self.event_bus.publish(event)
        except Exception as e:
            self._logger.error(f"Failed to publish to event bus: {e}")
        
        # Publish to message queue (async with retry)
        if self.message_queue:
            self._add_to_outbox('events', event)
    
    def publish_command(self, command: Command) -> None:
        """Publish a command to the message queue"""
        self._logger.info(f"Publishing command {command.command_type} (ID: {command.message_id})")
        
        if self.message_queue:
            self._add_to_outbox('commands', command)
    
    def publish_notification(self, notification: Notification) -> None:
        """Publish a notification"""
        self._logger.info(f"Publishing notification {notification.notification_type}")
        
        if self.message_queue:
            self._add_to_outbox('notifications', notification)
    
    def _add_to_outbox(self, topic: str, message: Message) -> None:
        """Add message to outbox for reliable delivery"""
        with self._outbox_lock:
            self._outbox.append((topic, message))
        
        # Start processing outbox if not already running
        if len(self._outbox) == 1:
            threading.Thread(target=self._process_outbox, daemon=True).start()
    
    def _process_outbox(self) -> None:
        """Process messages in the outbox with retry logic"""
        while self._outbox:
            with self._outbox_lock:
                if not self._outbox:
                    break
                topic, message = self._outbox[0]
            
            success = self._publish_with_retry(topic, message)
            
            with self._outbox_lock:
                if success:
                    # Remove from outbox
                    if self._outbox and self._outbox[0][1].message_id == message.message_id:
                        self._outbox.pop(0)
                else:
                    # Move to dead letter queue or keep retrying
                    self._logger.error(f"Failed to publish message {message.message_id} after retries")
                    if self._outbox and self._outbox[0][1].message_id == message.message_id:
                        self._outbox.pop(0)  # Remove to avoid infinite loop
                        # TODO: Move to dead letter queue
    
    def _publish_with_retry(self, topic: str, message: Message) -> bool:
        """Publish message with retry logic"""
        for attempt in range(self.max_retries):
            try:
                if self.message_queue:
                    return self.message_queue.publish(topic, message)
                return False
            except Exception as e:
                self._logger.warning(f"Attempt {attempt + 1} failed for message {message.message_id}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        
        return False
    
    def subscribe_to_events(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe to events on the event bus"""
        self.event_bus.subscribe(event_type, handler)
    
    def subscribe_to_queue(self, topic: str, callback: Callable[[Message], None]) -> str:
        """Subscribe to messages from a queue"""
        if self.message_queue:
            return self.message_queue.subscribe(topic, callback)
        raise RuntimeError("Message queue not configured")
    
    def replay_events(self, aggregate_id: UUID, handler: EventHandler) -> None:
        """Replay events for an aggregate"""
        if not self.event_store:
            raise RuntimeError("Event store not configured")
        
        events = self.event_store.get_events_for_aggregate(aggregate_id)
        
        for event in events:
            try:
                if handler.can_handle(event):
                    handler.handle(event)
            except Exception as e:
                self._logger.error(f"Error replaying event {event.event_type}: {e}")
    
    def close(self):
        """Close all messaging components"""
        if self.message_queue:
            self.message_queue.close()
        
        if self.event_store:
            self.event_store.close()
        
        self._logger.info("Message bus closed")


# ============================================================================
# EVENT HANDLER IMPLEMENTATIONS
# ============================================================================

class ParkingEventHandler(EventHandler):
    """Handles parking-related domain events"""
    
    def __init__(self, message_bus: Optional[MessageBus] = None):
        self.message_bus = message_bus
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def handle(self, event: DomainEvent) -> None:
        """Handle parking events"""
        if event.event_type == EventType.PARKING_SLOT_OCCUPIED:
            self._handle_slot_occupied(event)
        elif event.event_type == EventType.PARKING_SLOT_RELEASED:
            self._handle_slot_released(event)
        elif event.event_type == EventType.PARKING_LOT_STATUS_CHANGED:
            self._handle_lot_status_changed(event)
    
    def _handle_slot_occupied(self, event: DomainEvent) -> None:
        """Handle slot occupied event"""
        slot_id = event.data.get('slot_id')
        license_plate = event.data.get('license_plate')
        
        self._logger.info(f"Slot {slot_id} occupied by {license_plate}")
        
        # Send notification if message bus is available
        if self.message_bus:
            notification = Notification(
                notification_type="slot_occupied",
                title="Parking Slot Occupied",
                body=f"Slot {slot_id} is now occupied by {license_plate}",
                priority="normal"
            )
            self.message_bus.publish_notification(notification)
    
    def _handle_slot_released(self, event: DomainEvent) -> None:
        """Handle slot released event"""
        slot_id = event.data.get('slot_id')
        duration = event.data.get('duration_hours')
        fee = event.data.get('fee')
        
        self._logger.info(f"Slot {slot_id} released after {duration} hours, fee: {fee}")
    
    def _handle_lot_status_changed(self, event: DomainEvent) -> None:
        """Handle parking lot status change"""
        lot_id = event.data.get('parking_lot_id')
        occupancy_rate = event.data.get('occupancy_rate')
        
        self._logger.info(f"Parking lot {lot_id} occupancy: {occupancy_rate:.1%}")
        
        # Send alert if occupancy is high
        if occupancy_rate > 0.9:  # 90% occupancy
            alert = Alert(
                alert_type="high_occupancy",
                severity="warning",
                metric="occupancy_rate",
                value=occupancy_rate,
                threshold=0.9,
                message=f"Parking lot {lot_id} is {occupancy_rate:.1%} full"
            )
            
            if self.message_bus:
                self.message_bus.publish_event(
                    DomainEvent(
                        event_type=EventType.SYSTEM_ALERT,
                        data=alert.to_dict()
                    )
                )


class BillingEventHandler(EventHandler):
    """Handles billing-related domain events"""
    
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def handle(self, event: DomainEvent) -> None:
        """Handle billing events"""
        if event.event_type == EventType.INVOICE_CREATED:
            self._handle_invoice_created(event)
        elif event.event_type == EventType.PAYMENT_PROCESSED:
            self._handle_payment_processed(event)
    
    def _handle_invoice_created(self, event: DomainEvent) -> None:
        """Handle invoice created event"""
        invoice_id = event.data.get('invoice_id')
        amount = event.data.get('amount')
        
        self._logger.info(f"Invoice {invoice_id} created for ${amount}")
        
        # In a real system, this might:
        # 1. Send invoice email to customer
        # 2. Update accounting system
        # 3. Trigger payment reminder workflows
    
    def _handle_payment_processed(self, event: DomainEvent) -> None:
        """Handle payment processed event"""
        payment_id = event.data.get('payment_id')
        invoice_id = event.data.get('invoice_id')
        amount = event.data.get('amount')
        
        self._logger.info(f"Payment {payment_id} processed for invoice {invoice_id}: ${amount}")
        
        # In a real system, this might:
        # 1. Send payment confirmation email
        # 2. Update accounting records
        # 3. Release any holds on the vehicle


class NotificationEventHandler(AsyncEventHandler):
    """Async event handler for sending notifications"""
    
    def __init__(self, email_service=None, sms_service=None):
        self.email_service = email_service
        self.sms_service = sms_service
        self._logger = logging.getLogger(self.__class__.__name__)
    
    async def handle(self, event: DomainEvent) -> None:
        """Handle notification events asynchronously"""
        if event.event_type == EventType.RESERVATION_CONFIRMED:
            await self._handle_reservation_confirmed(event)
        elif event.event_type == EventType.SYSTEM_ALERT:
            await self._handle_system_alert(event)
    
    async def _handle_reservation_confirmed(self, event: DomainEvent) -> None:
        """Send reservation confirmation notification"""
        reservation_id = event.data.get('reservation_id')
        customer_email = event.data.get('customer_email')
        confirmation_code = event.data.get('confirmation_code')
        
        self._logger.info(f"Sending reservation confirmation for {reservation_id}")
        
        # Send email
        if self.email_service and customer_email:
            subject = "Parking Reservation Confirmed"
            body = f"Your reservation {reservation_id} is confirmed. Code: {confirmation_code}"
            
            try:
                await self.email_service.send(customer_email, subject, body)
                self._logger.debug(f"Reservation email sent to {customer_email}")
            except Exception as e:
                self._logger.error(f"Failed to send reservation email: {e}")
        
        # Send SMS if phone number provided
        phone_number = event.data.get('customer_phone')
        if self.sms_service and phone_number:
            message = f"Reservation {reservation_id} confirmed. Code: {confirmation_code}"
            
            try:
                await self.sms_service.send(phone_number, message)
                self._logger.debug(f"Reservation SMS sent to {phone_number}")
            except Exception as e:
                self._logger.error(f"Failed to send reservation SMS: {e}")
    
    async def _handle_system_alert(self, event: DomainEvent) -> None:
        """Handle system alerts"""
        alert_data = event.data
        alert_type = alert_data.get('alert_type')
        message = alert_data.get('message')
        
        self._logger.warning(f"System alert: {alert_type} - {message}")
        
        # In a real system, this might:
        # 1. Send alerts to monitoring dashboard
        # 2. Notify operations team
        # 3. Trigger automated responses


# ============================================================================
# MESSAGE BROKER FACTORY
# ============================================================================

class MessageBrokerFactory:
    """Factory for creating message brokers"""
    
    @staticmethod
    def create_redis_broker(redis_url: str = "redis://localhost:6379", **kwargs) -> RedisMessageQueue:
        """Create Redis message broker"""
        return RedisMessageQueue(redis_url, **kwargs)
    
    @staticmethod
    def create_rabbitmq_broker(amqp_url: str = "amqp://localhost:5672", **kwargs) -> RabbitMQMessageQueue:
        """Create RabbitMQ message broker"""
        return RabbitMQMessageQueue(amqp_url, **kwargs)
    
    @staticmethod
    def create_kafka_broker(bootstrap_servers: str = "localhost:9092", **kwargs) -> KafkaMessageQueue:
        """Create Kafka message broker"""
        return KafkaMessageQueue(bootstrap_servers, **kwargs)
    
    @staticmethod
    def create_in_memory_broker() -> 'InMemoryMessageQueue':
        """Create in-memory message broker (for testing)"""
        return InMemoryMessageQueue()
    
    @staticmethod
    def create_event_store(mongo_url: str = "mongodb://localhost:27017", **kwargs) -> EventStore:
        """Create event store"""
        return EventStore(mongo_url, **kwargs)
    
    @staticmethod
    def create_message_bus(
        broker_type: str = "redis",
        use_event_store: bool = True,
        **kwargs
    ) -> MessageBus:
        """Create a complete message bus with configured broker"""
        # Create broker
        if broker_type == "redis":
            broker = MessageBrokerFactory.create_redis_broker(**kwargs)
        elif broker_type == "rabbitmq":
            broker = MessageBrokerFactory.create_rabbitmq_broker(**kwargs)
        elif broker_type == "kafka":
            broker = MessageBrokerFactory.create_kafka_broker(**kwargs)
        elif broker_type == "memory":
            broker = MessageBrokerFactory.create_in_memory_broker()
        else:
            raise ValueError(f"Unknown broker type: {broker_type}")
        
        # Create event store
        event_store = None
        if use_event_store:
            event_store = MessageBrokerFactory.create_event_store(**kwargs)
        
        # Create message bus
        return MessageBus(
            event_bus=EventBus(),
            message_queue=broker,
            event_store=event_store
        )


# ============================================================================
# IN-MEMORY MESSAGE QUEUE (For Testing)
# ============================================================================

class InMemoryMessageQueue(MessageQueue):
    """In-memory message queue for testing"""
    
    def __init__(self):
        self._topics: Dict[str, List[Callable[[Message], None]]] = {}
        self._messages: Dict[str, List[Message]] = {}
        self._subscription_ids: Dict[str, str] = {}  # subscription_id -> topic
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def publish(self, topic: str, message: Message) -> bool:
        """Publish message to in-memory topic"""
        if topic not in self._topics:
            self._topics[topic] = []
            self._messages[topic] = []
        
        # Store message
        self._messages[topic].append(message)
        
        # Notify subscribers
        for callback in self._topics[topic]:
            try:
                callback(message)
            except Exception as e:
                self._logger.error(f"Error in callback for topic {topic}: {e}")
        
        self._logger.debug(f"Published to {topic}: {message.message_id}")
        return True
    
    def subscribe(self, topic: str, callback: Callable[[Message], None]) -> str:
        """Subscribe to in-memory topic"""
        if topic not in self._topics:
            self._topics[topic] = []
            self._messages[topic] = []
        
        subscription_id = str(uuid4())
        self._topics[topic].append(callback)
        self._subscription_ids[subscription_id] = topic
        
        self._logger.debug(f"Subscribed to {topic} with ID {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from topic"""
        if subscription_id not in self._subscription_ids:
            return False
        
        topic = self._subscription_ids[subscription_id]
        if topic in self._topics:
            # Find and remove callback (we don't track which callback belongs to which subscription)
            # In real implementation, we would track this mapping
            pass
        
        del self._subscription_ids[subscription_id]
        return True
    
    def create_topic(self, topic: str, **kwargs) -> bool:
        """Create in-memory topic"""
        if topic not in self._topics:
            self._topics[topic] = []
            self._messages[topic] = []
            return True
        return False
    
    def delete_topic(self, topic: str) -> bool:
        """Delete in-memory topic"""
        if topic in self._topics:
            del self._topics[topic]
            del self._messages[topic]
            
            # Remove subscriptions for this topic
            subscription_ids_to_remove = [
                sid for sid, t in self._subscription_ids.items() if t == topic
            ]
            for sid in subscription_ids_to_remove:
                del self._subscription_ids[sid]
            
            return True
        return False
    
    def get_messages(self, topic: str) -> List[Message]:
        """Get all messages for a topic (for testing)"""
        return self._messages.get(topic, []).copy()
    
    def clear(self):
        """Clear all messages and subscriptions (for testing)"""
        self._topics.clear()
        self._messages.clear()
        self._subscription_ids.clear()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Example usage of messaging infrastructure"""
    import time
    
    # Create a simple event handler for demonstration
    class DemoEventHandler(EventHandler):
        def handle(self, event: DomainEvent) -> None:
            print(f"Demo handler received: {event.event_type} - {event.message_id}")
    
    # Create message bus with Redis broker
    factory = MessageBrokerFactory()
    
    try:
        # Create message bus
        message_bus = factory.create_message_bus(
            broker_type="memory",  # Use in-memory for demo
            use_event_store=False
        )
        
        # Create event handlers
        demo_handler = DemoEventHandler()
        parking_handler = ParkingEventHandler(message_bus)
        
        # Subscribe handlers to events
        message_bus.event_bus.subscribe(EventType.PARKING_SLOT_OCCUPIED, demo_handler)
        message_bus.event_bus.subscribe(EventType.PARKING_SLOT_OCCUPIED, parking_handler)
        message_bus.event_bus.subscribe(EventType.PARKING_SLOT_RELEASED, demo_handler)
        
        # Subscribe to message queue
        def queue_callback(message: Message):
            print(f"Queue received: {message.message_type} - {message.message_id}")
        
        subscription_id = message_bus.subscribe_to_queue("events", queue_callback)
        
        # Publish some events
        print("\n=== Publishing Events ===")
        
        # Event 1: Parking slot occupied
        event1 = DomainEvent(
            event_type=EventType.PARKING_SLOT_OCCUPIED,
            aggregate_id=uuid4(),
            aggregate_type="ParkingSlot",
            data={
                "slot_id": "SLOT-001",
                "license_plate": "ABC-123",
                "vehicle_type": "car",
                "timestamp": datetime.now().isoformat()
            }
        )
        message_bus.publish_event(event1)
        
        # Event 2: Parking slot released
        event2 = DomainEvent(
            event_type=EventType.PARKING_SLOT_RELEASED,
            aggregate_id=uuid4(),
            aggregate_type="ParkingSlot",
            data={
                "slot_id": "SLOT-001",
                "license_plate": "ABC-123",
                "duration_hours": 2.5,
                "fee": 12.50,
                "timestamp": datetime.now().isoformat()
            }
        )
        message_bus.publish_event(event2)
        
        # Publish a command
        print("\n=== Publishing Command ===")
        command = Command(
            command_type=CommandType.PARK_VEHICLE,
            payload={
                "license_plate": "XYZ-789",
                "vehicle_type": "ev_car",
                "parking_lot_id": str(uuid4())
            }
        )
        message_bus.publish_command(command)
        
        # Wait a bit for async processing
        time.sleep(1)
        
        # Unsubscribe and close
        message_bus.message_queue.unsubscribe(subscription_id)
        message_bus.close()
        
        print("\n=== Example Complete ===")
        
    except Exception as e:
        print(f"Error in example: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example
    example_usage()