# Event-Driven Architecture - Parking Management System

## Overview

The Parking Management System leverages an event-driven architecture to achieve loose coupling, scalability, and real-time processing. This document details the event-driven patterns, message flows, and implementation strategies used throughout the system.

## Architecture Principles

### Core Principles

1. **Event-First Design**: Services communicate primarily through events
2. **Loose Coupling**: Services are independent and unaware of each other
3. **Event Sourcing**: State changes are captured as a sequence of events
4. **Eventual Consistency**: Systems converge to consistency over time
5. **Reactive Systems**: Responsive, resilient, elastic, and message-driven

### Technology Stack

- **Message Broker**: Apache Kafka with KRaft mode
- **Event Schema**: Apache Avro with Schema Registry
- **Event Processing**: Kafka Streams, Spring Cloud Stream
- **CDC (Change Data Capture)**: Debezium
- **Event Store**: Apache Pulsar for long-term event storage
- **Monitoring**: Kafka Manager, Prometheus, Grafana