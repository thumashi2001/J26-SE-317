# AdaptiveLearnSE Backend

This directory contains one Node.js + Express application. Authentication and C1-C4 are modular areas under `src/modules/`, while shared application concerns remain under `src/config/`, `src/middleware/`, and `src/integration/`.

The component directories are integration boundaries, not independent backend servers. Heavy AI/ML processing belongs in the corresponding Python service under `ai-services/`.

The backend is currently structural only; routes, controllers, services, models, validators, and application startup logic will be implemented in later phases.
