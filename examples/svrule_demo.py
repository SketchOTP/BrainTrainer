"""Small semantic reference example; not a live-game or whole-brain test."""
import json
from creature_brain.svrule import Context, Instruction, Program, execute

context = Context()
program = Program.of(
    Instruction(3, 11, 124),  # Load literal 124/248 = 0.5.
    Instruction(2, 3, 0),    # Bounded store to current neuron variable 0.
)
result = execute(program, context)
print(json.dumps({"scope": "SVRule mathematical reference example",
                  "neuron_state": context.neuron,
                  "executed_instructions": result.executed_instructions,
                  "stop_reason": result.stop_reason}, indent=2))
