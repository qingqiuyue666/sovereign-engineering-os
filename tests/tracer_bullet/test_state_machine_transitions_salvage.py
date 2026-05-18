import unittest

from kernel.errors.hierarchy import InvalidTransitionError
from kernel.state.machine import StateMachine, Transition
from kernel.state.transitions import TaskLifecycle, build_task_lifecycle


class StateMachineTests(unittest.TestCase):
    def test_observed_at_is_excluded_from_transition_hash(self):
        transitions = (Transition("INTAKE", "VALIDATED"),)
        first = StateMachine("INTAKE", transitions, name="unit")
        second = StateMachine("INTAKE", transitions, name="unit")

        first_receipt = first.fire("VALIDATED", observed_at="2026-01-01T00:00:00Z")
        second_receipt = second.fire("VALIDATED", observed_at="2027-01-01T00:00:00Z")

        self.assertNotEqual(first_receipt.observed_at, second_receipt.observed_at)
        self.assertEqual(first_receipt.content_hash, second_receipt.content_hash)
        self.assertEqual(first.deterministic_history(), second.deterministic_history())

    def test_guard_context_required_and_raw_context_rejected(self):
        machine = StateMachine("PLANNED", (Transition("PLANNED", "DRY_RUN_COMPLETE", required_context={"dry_run_only": True}),))

        with self.assertRaises(InvalidTransitionError):
            machine.fire("DRY_RUN_COMPLETE", context={"dry_run_only": False})
        with self.assertRaises(InvalidTransitionError):
            machine.fire("DRY_RUN_COMPLETE", context={"dry_run_only": True, "raw_prompt": "forbidden"})

        receipt = machine.fire("DRY_RUN_COMPLETE", context={"dry_run_only": True})
        self.assertTrue(receipt.accepted)

    def test_task_lifecycle_is_dry_run_only(self):
        machine = build_task_lifecycle("task_1")
        self.assertEqual(machine.state, TaskLifecycle.INTAKE.value)
        machine.fire(TaskLifecycle.VALIDATED.value)
        machine.fire(TaskLifecycle.PLANNED.value)

        with self.assertRaises(InvalidTransitionError):
            machine.fire(TaskLifecycle.DRY_RUN_COMPLETE.value)
        receipt = machine.fire(TaskLifecycle.DRY_RUN_COMPLETE.value, context={"dry_run_only": True})
        self.assertEqual(receipt.to_state, TaskLifecycle.DRY_RUN_COMPLETE.value)


if __name__ == "__main__":
    unittest.main()
