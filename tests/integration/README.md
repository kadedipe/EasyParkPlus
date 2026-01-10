# Integration Tests - Parking Management System

This directory contains integration tests for the Parking Management System.

## Overview

Integration tests verify that different components of the system work together correctly. Unlike unit tests that test individual components in isolation, integration tests ensure that the components interact properly.

## Test Categories

### 1. GUI + Controller Integration
Tests the interaction between the user interface (Tkinter GUI) and the application controller.

### 2. Service Layer Integration
Tests the business service layer and its interactions with repositories, factories, and message buses.

### 3. Command Processor Integration
Tests the command pattern implementation for undo/redo functionality.

### 4. End-to-End Scenarios
Tests complete user workflows from GUI input to database persistence.

### 5. Data Flow Integration
Tests data passing between different layers and components.

### 6. Event Handling
Tests user interaction and event handling across components.

### 7. Error Recovery
Tests system resilience and error handling.

### 8. Performance Integration
Tests performance aspects of integrated components.

## Running Tests

### Run All Integration Tests
```bash
python tests/integration/test_runner.py