from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_project


class ActionPinAuditTests(unittest.TestCase):
    def test_mutable_actions_fail_for_named_and_direct_step_syntax(self):
        for step in ('      - uses: actions/checkout@v7',
                     '      - name: Checkout\n        uses: actions/checkout@main',
                     '    uses: ./scripts/unreviewed-action',
                     '    uses: ./.github/workflows/smoke.yml@main'):
            with self.subTest(step=step), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'validate.yml').write_text('steps:\n' + step + '\n')
                with patch.object(audit_project, 'ROOT', root), patch.object(audit_project, 'WORKFLOWS', root):
                    with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                        audit_project.validate_action_pinning()

    def test_full_commit_is_accepted_for_both_step_syntaxes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'validate.yml').write_text('steps:\n  - uses: actions/checkout@' + 'a' * 40 + '\n'
                '  - name: Setup\n    uses: actions/setup-python@' + 'b' * 40 + '\n')
            with patch.object(audit_project, 'WORKFLOWS', root):
                audit_project.validate_action_pinning()

    def test_repository_local_reusable_workflow_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.yml').write_text('jobs:\n  smoke:\n    uses: ./.github/workflows/android-smoke.yml\n')
            with patch.object(audit_project, 'WORKFLOWS', root):
                audit_project.validate_action_pinning()
