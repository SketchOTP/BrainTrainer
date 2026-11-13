# BrainTrainer — Creature Brain

A research codebase for developing a persistent, embodied digital companion from a recovered Creatures brain. The working end goal and evidence criteria are in [docs/END_GOAL.md](docs/END_GOAL.md). Earlier gap assessments and development snapshots are archived in [docs/END_GOAL_CURRENT_AUDIT.md](docs/END_GOAL_CURRENT_AUDIT.md) and [docs/DEVELOPMENT_STATUS.md](docs/DEVELOPMENT_STATUS.md); consult their dates before treating them as current status.

The code includes the genome-driven brain and body research simulator, a developmental companion candidate, a browser habitat, retained learning and memory, reflective/self-review workflows, real-world action trials, and the sprite animation pipeline. These components demonstrate parts of the goal; they do not establish that the complete end goal has been achieved.

## Run the research simulator

Requires Python 3.12 or newer. Install the package in a virtual environment:

```sh
python -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m creature_brain --help
```

A recovered or otherwise authorized genome/program file is required for a creature run. Research data and recovered genome files are intentionally not included in this public repository:

```sh
.venv/bin/python -m creature_brain --genome /path/to/authorized-brain-program.json --steps 400 --output runs/demo
```

The CLI writes a checkpoint, summary, trajectory and replay page under the chosen output directory. Treat those as private runtime state; they are ignored by Git.

## Companion habitat and assets

The developmental habitat is in `examples/persistent_individual/`. Its entry point and controls are described in [docs/CONTINUING_HABITAT.md](docs/CONTINUING_HABITAT.md). A full town map pack is needed to run the top-down environment. Porymap/ROM-derived map files and extracted game graphics are not distributed here; see [the world asset note](examples/persistent_individual/assets/world/README.md).

The creature sprite sheets under `examples/persistent_individual/assets/creature/` are included as project art. Their provenance is recorded alongside them. The duplicate sprite archive and local generation paths are omitted.

## Development

- Python package: `src/creature_brain/`
- Continuing individual, habitat and environment: `examples/persistent_individual/`
- Focused source tests: `tests/`
- Research protocols and results: `docs/`
- Publication boundaries and omitted local inputs: [docs/PUBLICATION_SCOPE.md](docs/PUBLICATION_SCOPE.md)

The full historical test inventory is not present in this public branch because many tests depend on local recovered genomes, private runtime snapshots, or Pory/ROM-derived fixtures. The included tests are a source subset and were not run as part of this publication.
