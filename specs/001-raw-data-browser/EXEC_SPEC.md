# Execution Specification: Raw Data Browser

This document serves as an implementation guide for a development agent to complete the Raw Data Browser feature. It outlines how to use the files within the `specs/001-raw-data-browser/` directory to execute the development plan.

## Development Workflow

The development process is broken down into a series of sequential steps, where each step utilizes one or more files from the `specs/001-raw-data-browser/` directory to guide the implementation. The agent should follow these steps in order to ensure the feature is implemented correctly and according to the specification.

## Order of Operations

### 1. Understand the Feature

*   **Task**: Gain a comprehensive understanding of the feature's requirements, user stories, and success criteria.
*   **File(s)**:
    *   `spec.md`: This is the primary source of truth for the feature. It contains the user stories, functional requirements, and success criteria.
    *   `plan.md`: This file provides a high-level summary of the feature and the technical approach.

### 2. Backend Implementation

*   **Task**: Implement the backend functionality for the Raw Data Browser.
*   **File(s)**:
    *   `contracts/openapi.yaml`: Use this file to implement the `GET /api/raw-records` endpoint in `api/main.py`. It defines the API contract, including the endpoint path, parameters, and responses.
    *   `data-model.md`: This file provides the data models for the different record types. Use this to implement the database query logic to fetch the correct data from MongoDB.
    *   `exec.md`: This file provides the step-by-step execution plan for the backend implementation.

### 3. Frontend Implementation

*   **Task**: Implement the frontend functionality for the Raw Data Browser.
*   **File(s)**:
    *   `spec.md`: The functional requirements in this file will guide the implementation of the UI and user interactions.
    *   `research.md`: This file contains the decision to use `highlight.js` for syntax highlighting. The agent should use this information to integrate the library into the frontend.
    *   `exec.md`: This file provides the step-by-step execution plan for the frontend implementation.

### 4. Testing and Validation

*   **Task**: Test the implemented feature to ensure it meets the requirements.
*   **File(s)**:
    *   `spec.md`: The acceptance scenarios in the user stories should be used as a basis for testing.
    *   `checklists/requirements.md`: This file provides a checklist to validate that all requirements have been met.

### 5. User Guide

*   **Task**: Understand how the feature is intended to be used by the end-user.
*   **File(s)**:
    *   `quickstart.md`: This file provides a brief guide on how to use the new Raw Data Browser feature. This can be used to verify that the implementation matches the intended user experience.
