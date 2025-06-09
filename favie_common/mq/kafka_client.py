"""Kafka asynchronous client wrapper."""

import asyncio
import json
import logging
import os
from typing import AsyncGenerator, Dict, Iterable, Optional, Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

logger = logging.getLogger(__name__)


class KafkaClient:
    """Simple async Kafka producer and consumer wrapper with SASL authentication support."""

    def __init__(
        self, 
        bootstrap_servers: Optional[str] = None, 
        security_protocol: Optional[str] = None,
        sasl_mechanism: Optional[str] = None,
        sasl_username: Optional[str] = None,
        sasl_password: Optional[str] = None,
        group_id: str = "favie",
        **kwargs
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        
        # Build producer config
        producer_config = {
            'bootstrap_servers': self.bootstrap_servers,
            **kwargs
        }
        
        # Add SASL authentication if provided
        if security_protocol and sasl_mechanism and sasl_username and sasl_password:
            producer_config.update({
                'security_protocol': security_protocol,
                'sasl_mechanism': sasl_mechanism,
                'sasl_plain_username': sasl_username,
                'sasl_plain_password': sasl_password,
            })
        
        # Build consumer config
        consumer_config = {
            'bootstrap_servers': self.bootstrap_servers,
            'group_id': self.group_id,
            **producer_config
        }
        consumer_config.pop('group_id', None)  # Remove duplicate group_id
        
        self.producer = AIOKafkaProducer(**producer_config)
        self.consumer = None
        self._consumer_config = consumer_config

    async def start_producer(self) -> None:
        """Start the Kafka producer."""
        await self.producer.start()
        logger.info("Kafka producer started")

    async def start_consumer(self, topics: Iterable[str]) -> None:
        """Start the Kafka consumer for specific topics."""
        if self.consumer is None:
            self.consumer = AIOKafkaConsumer(*topics, **self._consumer_config)
        await self.consumer.start()
        logger.info(f"Kafka consumer started for topics: {list(topics)}")

    async def start(self, topics: Optional[Iterable[str]] = None) -> None:
        """Start both producer and optionally consumer."""
        await self.start_producer()
        if topics:
            await self.start_consumer(topics)

    async def stop(self) -> None:
        """Stop both producer and consumer."""
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")
        await self.producer.stop()
        logger.info("Kafka producer stopped")

    async def send_message(
        self, 
        topic: str, 
        message: Dict[str, Any], 
        key: Optional[str] = None
    ) -> None:
        """Send a JSON message to Kafka topic."""
        try:
            message_bytes = json.dumps(message, ensure_ascii=False).encode('utf-8')
            key_bytes = key.encode('utf-8') if key else None
            
            await self.producer.send_and_wait(topic, value=message_bytes, key=key_bytes)
            logger.info(f"Message sent to topic '{topic}' successfully")
            
        except Exception as e:
            logger.error(f"Failed to send message to topic '{topic}': {e}")
            raise

    async def send_raw(self, topic: str, value: bytes, key: Optional[bytes] = None) -> None:
        """Send raw bytes to Kafka topic."""
        await self.producer.send_and_wait(topic, value=value, key=key)

    async def consume(self, topics: Iterable[str]) -> AsyncGenerator:
        """Consume messages from Kafka topics."""
        if self.consumer is None:
            await self.start_consumer(topics)
        
        async for message in self.consumer:
            yield message
