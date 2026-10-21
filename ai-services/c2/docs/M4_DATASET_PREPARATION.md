# M4 — Multi-Module Dataset Preparation

## Overview

Milestone M4 establishes the configuration and validation
foundation for eight Year 3 Software Engineering modules.

## Implemented Components

### Module Configuration

- Defines eight modules across two semesters.
- Preserves unknown module codes and examination structures.
- Uses a versioned JSON configuration.

### Module Registry

- Loads and validates module configurations.
- Supports module lookup by key and code.
- Validates module identifiers and semester assignments.

### Dataset Coverage Tracker

- Calculates paper and question coverage by module.
- Separates authentic and synthetic dataset statistics.
- Tracks marks warnings.
- Detects duplicate question IDs and unknown modules.

### Synthetic Dataset Preparation

- Defines generation and quality policies.
- Checks module readiness before generation.
- Validates basic synthetic question fields.
- Requires explicit synthetic provenance.

## Current Dataset Status

Initial testing uses one authentic Database Systems
examination paper containing 25 structured question records.

This is not sufficient to establish representative
examination patterns across all eight modules.

## Known Limitations

- Most module codes and topic lists require verification.
- Module-specific examination structures remain unconfigured.
- Synthetic examination generation is not yet implemented.
- Current question validation does not enforce all paper-level rules.
- Additional authentic examination papers are required.

## Next Steps

1. Collect and verify module-specific reference materials.
2. Define examination structures and topic taxonomies.
3. Implement controlled synthetic question generation.
4. Extend validation across all eight modules.
5. Integrate C2 services with backend and frontend.
