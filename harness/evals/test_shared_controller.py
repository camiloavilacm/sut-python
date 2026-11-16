"""Regression coverage for the consolidated registry and maintenance boundary."""
import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import ROOT, permitted
from verify_step import command
class SharedController(unittest.TestCase):
 def test_wrong_repository_cannot_execute_another_runner_check(self):
  with patch('verify_step.state',return_value={'authorized_step':'3'}),patch('verify_step.location',return_value={'repository':'qa-typescript'}):
   with self.assertRaises(ValueError):command(ROOT,'12-passes')
 def test_future_checks_are_not_registered(self):
  with patch('verify_step.state',return_value={'authorized_step':'5'}):
   with self.assertRaises(ValueError):command(ROOT,'sandbox-comment')
 def test_arbitrary_command_is_rejected(self):
  with self.assertRaises(ValueError):command(ROOT,'python -c pass')
 def test_maintenance_cannot_modify_application_or_contract(self):
  for name in ('app.py','cypress/e2e/auth.cy.ts','features/auth/login.feature','schemas/results.schema.json'):
   self.assertFalse(permitted(ROOT,'4',name))
if __name__=='__main__':unittest.main()
