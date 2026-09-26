# Locked configuration

Phase 5 configuration SHA-256: `b8ed0c15737a61c2c3882de0bedf0ffb3e0d442299e631aeb74a9cc85f021fce`

The authoritative machine-readable configuration is `configs/experiments/phase5_locked.yaml`. It fixes the primary I3-versus-I0 comparison, 2,000 participant-bootstrap replicates, training-fold target-SD standardization, figure/table inventory, and exact private prediction-input verification.

## Generating configurations

- Phase 3: `e9ea6569551979ce01740261f7955f09218e4749774710977b3bbaab1f84c63b`
- Phase 4: `9c8e2708d6a1fa8257fe890b8c67520715375b429ab2f4f3e26d6687506470ef`

Prediction rows retain their original generating Git commits. Phase 5 does not rewrite this provenance; it verifies exact artifact hashes before analysis.
