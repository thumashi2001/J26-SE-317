# AdaptiveLearnSE

AdaptiveLearnSE is an undergraduate research project for an integrated AI-powered adaptive learning ecosystem. The repository is currently being prepared as a modular monorepo; application functionality will be developed incrementally.

## Research Components

- **C1 - Cognitive Digital Twin:** models learner-related cognitive state and evidence.
- **C2 - AI-Based Exam Intelligence System:** supports assessment and exam intelligence workflows.
- **C3 - AI-Powered Automated Marking and Answer Analysis System:** processes answers, supports marking, analyses concepts, and generates explainable evidence.
- **C4 - Reinforcement Learning-Based Adaptive Learning System:** investigates adaptive learning decisions using reinforcement learning.

## Architecture

AdaptiveLearnSE uses one repository containing one React frontend and one Node.js + Express backend. The backend is a single application with separate modules for authentication and C1-C4 under `backend/src/modules/`. This keeps shared integration, security, and operational concerns in one place while allowing each research component to be developed independently.

The AI/ML processing is separated into Python services by component. This gives research code appropriate Python tooling and independent experiment boundaries without creating unnecessary Node.js servers or microservice infrastructure. Components communicate through clearly defined REST/JSON interfaces.

MongoDB Atlas is intended for operational and application data. Neo4j is intended for the shared Curriculum Knowledge Graph (CCKG). These databases have distinct responsibilities and are not duplicated per component.

## Repository Structure

```text
frontend/       One React application
backend/        One modular Express application
ai-services/    Python AI service boundaries for C1-C4
database/       MongoDB and Neo4j structure and notes
docs/           Architecture, API, research, experiment, meeting, and PP1 material
tests/          Cross-component integration and end-to-end test areas
```

## Development Ownership

Each component can be independently researched within its backend module, Python AI service, experiments, tests, and documentation areas. C3 is the primary component for this research project. Shared interfaces and infrastructure should be coordinated across component ownership boundaries.

## Current Status

This repository contains structure and planning documentation only. C1, C2, C3, and C4 are not claimed to be implemented. APIs, models, datasets, and research functionality will be added in later phases.