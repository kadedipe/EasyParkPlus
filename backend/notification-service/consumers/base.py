"""
Base consumer class for all notification consumers.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, Awaitable
from datetime import datetime
from contextlib import asynccontextmanager

import aio_pika
from aio_pika import Message, IncomingMessage, ExchangeType
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel, AbstractQueue

from ..core.config import settings
from ..core.exceptions import ConsumerError
from ..utils.logging_utils import get_logger, audit_log
from ..utils.metrics import track_consumer_metrics
from ..utils.retry import async_retry


class BaseConsumer(ABC):
    """
    Base class for all message consumers.
    """
    
    def __init__(
        self,
        queue_name: str,
        exchange_name: str = "notifications",
        routing_key: str = "#",
        prefetch_count: int = 10,
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        """
        Initialize base consumer.
        
        Args:
            queue_name: Name of the queue
            exchange_name: Name of the exchange
            routing_key: Routing key for binding
            prefetch_count: Number of messages to prefetch
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.queue_name = queue_name
        self.exchange_name = exchange_name
        self.routing_key = routing_key
        self.prefetch_count = prefetch_count
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.connection: Optional[AbstractRobustConnection] = None
        self.channel: Optional[AbstractRobustChannel] = None
        self.queue: Optional[AbstractQueue] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        
        self.logger = get_logger(f"{self.__class__.__name__}")
        self.is_running = False
        self.consumer_tag: Optional[str] = None
    
    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> bool:
        """
        Process a single message.
        
        Args:
            message: Message data
            
        Returns:
            bool: True if processing succeeded, False otherwise
        """
        pass
    
    async def connect(self) -> None:
        """
        Establish connection to RabbitMQ.
        """
        try:
            # Create connection
            self.connection = await aio_pika.connect_robust(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                login=settings.RABBITMQ_USER,
                password=settings.RABBITMQ_PASSWORD,
                virtualhost=settings.RABBITMQ_VHOST,
                timeout=30
            )
            
            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=self.prefetch_count)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                name=self.exchange_name,
                type=ExchangeType.TOPIC,
                durable=True,
                auto_delete=False
            )
            
            # Declare queue
            self.queue = await self.channel.declare_queue(
                name=self.queue_name,
                durable=True,
                auto_delete=False,
                arguments={
                    "x-max-priority": 10,
                    "x-dead-letter-exchange": f"{self.exchange_name}.dlx",
                    "x-dead-letter-routing-key": f"{self.queue_name}.dead"
                }
            )
            
            # Bind queue to exchange
            await self.queue.bind(
                exchange=self.exchange,
                routing_key=self.routing_key
            )
            
            self.logger.info(
                f"Connected to RabbitMQ. Queue: {self.queue_name}, "
                f"Exchange: {self.exchange_name}, Routing Key: {self.routing_key}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise ConsumerError(f"Connection failed: {e}")
    
    async def disconnect(self) -> None:
        """
        Close connection to RabbitMQ.
        """
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            self.logger.info("Disconnected from RabbitMQ")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def setup_dead_letter_queue(self) -> None:
        """
        Setup dead letter queue for failed messages.
        """
        try:
            # Create dead letter exchange
            dlx = await self.channel.declare_exchange(
                name=f"{self.exchange_name}.dlx",
                type=ExchangeType.TOPIC,
                durable=True
            )
            
            # Create dead letter queue
            dlq = await self.channel.declare_queue(
                name=f"{self.queue_name}.dead",
                durable=True,
                arguments={
                    "x-message-ttl": 86400000,  # 24 hours
                    "x-max-length": 10000
                }
            )
            
            # Bind dead letter queue
            await dlq.bind(
                exchange=dlx,
                routing_key=f"{self.queue_name}.dead"
            )
            
            self.logger.info(f"Dead letter queue setup complete for {self.queue_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to setup dead letter queue: {e}")
            raise
    
    async def handle_message(self, message: IncomingMessage) -> None:
        """
        Handle incoming message.
        
        Args:
            message: Incoming message
        """
        async with message.process(ignore_processed=True):
            try:
                # Parse message
                body = message.body.decode()
                data = json.loads(body)
                
                self.logger.info(f"Received message: {data.get('type', 'unknown')}")
                
                # Add message metadata
                data["_metadata"] = {
                    "message_id": message.message_id,
                    "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                    "retry_count": message.headers.get("x-retry-count", 0) if message.headers else 0,
                    "queue": self.queue_name
                }
                
                # Process message
                with track_consumer_metrics(self.queue_name):
                    success = await self.process_message(data)
                
                if success:
                    # Acknowledge message
                    await message.ack()
                    self.logger.info(f"Message {message.message_id} processed successfully")
                    
                    # Audit log
                    audit_log(
                        self.logger,
                        action="MESSAGE_PROCESSED",
                        resource="notification",
                        resource_id=message.message_id,
                        details={"queue": self.queue_name, "type": data.get('type')}
                    )
                else:
                    # Handle failure
                    await self.handle_failure(message, data)
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse message JSON: {e}")
                await message.reject(requeue=False)  # Reject permanently
                
            except Exception as e:
                self.logger.error(f"Error processing message: {e}", exc_info=True)
                await self.handle_failure(message, data if 'data' in locals() else {})
    
    async def handle_failure(self, message: IncomingMessage, data: Dict[str, Any]) -> None:
        """
        Handle message processing failure.
        
        Args:
            message: Failed message
            data: Message data
        """
        retry_count = message.headers.get("x-retry-count", 0) if message.headers else 0
        
        if retry_count < self.max_retries:
            # Retry with delay
            self.logger.warning(
                f"Message {message.message_id} failed. "
                f"Retry {retry_count + 1}/{self.max_retries}"
            )
            
            # Add retry header
            headers = message.headers or {}
            headers["x-retry-count"] = retry_count + 1
            headers["x-last-error"] = str(data.get("error", "Unknown error"))
            
            # Republish with delay
            await asyncio.sleep(self.retry_delay * (2 ** retry_count))  # Exponential backoff
            
            await self.exchange.publish(
                Message(
                    body=message.body,
                    headers=headers,
                    message_id=message.message_id,
                    priority=message.priority,
                    expiration=self.get_retry_expiration(retry_count)
                ),
                routing_key=message.routing_key or self.routing_key
            )
            
            await message.ack()  # Acknowledge original message
        else:
            # Send to dead letter queue
            self.logger.error(
                f"Message {message.message_id} exceeded max retries. "
                f"Sending to dead letter queue"
            )
            
            # Create dead letter message
            dlx = await self.channel.get_exchange(f"{self.exchange_name}.dlx")
            await dlx.publish(
                Message(
                    body=message.body,
                    headers={
                        **message.headers,
                        "x-dead-letter-reason": "max_retries_exceeded",
                        "x-dead-letter-time": datetime.utcnow().isoformat()
                    },
                    message_id=message.message_id
                ),
                routing_key=f"{self.queue_name}.dead"
            )
            
            await message.reject(requeue=False)  # Reject permanently
            
            # Audit log for dead letter
            audit_log(
                self.logger,
                action="MESSAGE_DEAD_LETTER",
                resource="notification",
                resource_id=message.message_id,
                details={
                    "queue": self.queue_name,
                    "retries": retry_count,
                    "reason": "max_retries_exceeded"
                },
                level="ERROR"
            )
    
    def get_retry_expiration(self, retry_count: int) -> int:
        """
        Get expiration time for retry message.
        
        Args:
            retry_count: Current retry count
            
        Returns:
            int: Expiration time in milliseconds
        """
        # Exponential backoff: 1min, 5min, 15min
        delays = [60000, 300000, 900000]
        return delays[retry_count] if retry_count < len(delays) else 3600000
    
    async def start(self) -> None:
        """
        Start consuming messages.
        """
        try:
            # Connect if not connected
            if not self.connection or self.connection.is_closed:
                await self.connect()
            
            # Setup dead letter queue
            await self.setup_dead_letter_queue()
            
            # Start consuming
            self.consumer_tag = await self.queue.consume(
                callback=self.handle_message,
                no_ack=False
            )
            
            self.is_running = True
            self.logger.info(f"Started consuming from queue: {self.queue_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to start consumer: {e}")
            raise
    
    async def stop(self) -> None:
        """
        Stop consuming messages.
        """
        if self.consumer_tag and self.queue:
            await self.queue.cancel(self.consumer_tag)
            self.logger.info(f"Stopped consuming from queue: {self.queue_name}")
        
        await self.disconnect()
        self.is_running = False
    
    @asynccontextmanager
    async def consumer_context(self):
        """
        Context manager for consumer lifecycle.
        """
        try:
            await self.start()
            yield self
        finally:
            await self.stop()
    
    async def run_forever(self) -> None:
        """
        Run consumer forever.
        """
        self.logger.info(f"Starting {self.__class__.__name__}")
        
        try:
            await self.start()
            
            # Keep running
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Consumer error: {e}")
        finally:
            await self.stop()
            self.logger.info(f"{self.__class__.__name__} stopped")
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get queue status.
        
        Returns:
            Dict[str, Any]: Queue status information
        """
        if not self.queue:
            return {}
        
        queue_info = await self.queue.declare(passive=True)
        
        return {
            "name": queue_info.name,
            "consumer_count": queue_info.consumer_count,
            "message_count": queue_info.message_count,
            "unacknowledged_count": queue_info.unacknowledged_message_count
        }