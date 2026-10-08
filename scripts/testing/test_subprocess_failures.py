"""Test subprocess failure handling without importing or running Emme/Daysim."""
import ast
import datetime
import os
import math
import getopt
import tempfile
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch


def runner_functions():
    source = Path(__file__).resolve().parents[2] / 'run_bkrcast.py'
    tree = ast.parse(source.read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    for node in functions:
        node.decorator_list = []
    namespace = dict(subprocess=Mock(), sys=sys, os=os, datetime=datetime, math=math, tempfile=tempfile, getopt=getopt,
                     logger=Mock(), copy_accessibility_files=Mock(),
                     run_daysim=True, run_skims_and_paths=True,
                     run_supplemental_trips=True, run_truck_model=True)
    namespace['subprocess'].CalledProcessError = subprocess.CalledProcessError
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), namespace)
    return namespace


class SubprocessFailureTests(unittest.TestCase):
    def test_relative_synthetic_population_path_rejected_before_precheck(self):
        ns = runner_functions()
        ns['precheck'] = Mock()
        with patch.object(sys, 'argv', ['run_bkrcast.py', '-s', 'population']), patch('builtins.print'):
            with self.assertRaises(SystemExit) as error:
                ns['main']()
        self.assertEqual(error.exception.code, 2)
        ns['precheck'].assert_not_called()

    def test_atomic_rmse_write_preserves_history_on_failure(self):
        source = Path(__file__).resolve().parents[2] / 'scripts/utils/shadow_pricing_check.py'
        tree = ast.parse(source.read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'write_rmse')
        ns = dict(os=os, math=math, tempfile=tempfile)
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), ns)
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / 'rmse.txt'
            result.write_text('30\n')
            with patch('os.replace', side_effect=OSError('replace failed')):
                with self.assertRaises(OSError):
                    ns['write_rmse'](str(result), 12.5, append=True)
            self.assertEqual(result.read_text(), '30\n')
            self.assertEqual(list(Path(directory).iterdir()), [result])
            ns['write_rmse'](str(result), 12.5, append=True)
            self.assertEqual(result.read_text(), '30\n12.5\n')
            ns['write_rmse'](str(result), 10)
            self.assertEqual(result.read_text(), '10\n')
            with self.assertRaises(ValueError):
                ns['write_rmse'](str(result), float('nan'))
            self.assertEqual(result.read_text(), '10\n')

    def test_shadow_result_must_be_fresh_and_valid(self):
        for content in (None, '', 'garbage', 'nan', 'inf', '-1', '1\n2'):
            with self.subTest(content=content):
                ns = runner_functions()
                self.assertIn('check_shadow_rmse', ns)
                def write_result(command, **kwargs):
                    if content is not None:
                        Path(command[-1]).write_text(content)
                ns['subprocess'].run.side_effect = write_result
                with self.assertRaises(SystemExit) as error:
                    ns['check_shadow_rmse']()
                self.assertEqual(error.exception.code, 1)

    def test_shadow_result_is_read_and_temporary_file_removed(self):
        ns = runner_functions()
        self.assertIn('check_shadow_rmse', ns)
        paths = []
        def write_result(command, **kwargs):
            paths.append(Path(command[-1]))
            paths[-1].write_text('12.5\n')
        ns['subprocess'].run.side_effect = write_result
        self.assertEqual(ns['check_shadow_rmse'](), 12.5)
        self.assertFalse(paths[0].exists())

    def test_generic_subprocess_helper_handles_default_environment(self):
        ns = runner_functions()
        self.assertIn('run_subprocess', ns)
        ns['subprocess'].run.side_effect = subprocess.CalledProcessError(1, ['command'])
        with self.assertRaises(SystemExit) as error:
            ns['run_subprocess'](['command'])
        self.assertEqual(error.exception.code, 1)
        self.assertEqual(ns['logger'].exception.call_args.args[0],
                         'Subprocess failed. Command: %s. Error: %s')

    def test_failed_quarto_render_preserves_existing_summary(self):
        source = Path(__file__).resolve().parents[2] / 'run_bkrcast_validation.py'
        tree = ast.parse(source.read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'create_quarto_notebook')
        ns = dict(os=Mock(), subprocess=subprocess, shutil=Mock(),
                  run_ipynb=Mock(), project_folder='project')
        ns['os'].system.return_value = 1
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), ns)
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['quarto'])):
            with patch('builtins.print'), self.assertRaises(subprocess.CalledProcessError):
                ns['create_quarto_notebook']('validation', [], 'notebooks', '_book')
        ns['shutil'].rmtree.assert_not_called()
        ns['shutil'].move.assert_not_called()

    def test_each_enabled_summary_failure_stops_run(self):
        flags = ('run_bkrcast_summary', 'run_create_daily_bank', 'run_landuse_summary',
                 'run_truck_summary', 'run_vmt_summary', 'run_telecommute_summary',
                 'run_modeshare_summary')
        for flag in flags:
            for year in ('2023', '2025'):
                with self.subTest(flag=flag, year=year):
                    ns = runner_functions()
                    ns.update(dict.fromkeys(flags, False))
                    ns.update(model_year=year)
                    ns[flag] = True
                    ns['subprocess'].run.side_effect = subprocess.CalledProcessError(1, ['summary'])
                    with self.assertRaises(SystemExit) as error:
                        ns['run_all_summaries']()
                    self.assertEqual(error.exception.code, 1)
                    self.assertEqual(ns['subprocess'].run.call_count, 1)
                    ns['logger'].exception.assert_called_once()

    def test_nonzero_exits_stop_each_model_stage(self):
        for code in (1, 3221225477, -1073741819):
            for function, args in (('accessibility_calcs', ()), ('build_seed_skims', (10,)),
                                   ('daysim_assignment', (0,)), ('run_truck_supplemental', (0,)),
                                   ('run_recreational_bike', ())):
                with self.subTest(code=code, function=function):
                    ns = runner_functions()
                    ns['subprocess'].run.side_effect = subprocess.CalledProcessError(code, ['model'])
                    with patch('builtins.print'), self.assertRaises(SystemExit) as error:
                        ns[function](*args)
                    self.assertEqual(error.exception.code, 1)
                    self.assertEqual(ns['subprocess'].run.call_count, 1)
                    self.assertTrue(ns['subprocess'].run.call_args.kwargs['check'])
                    ns['logger'].exception.assert_called_once()
                    self.assertEqual(ns['logger'].exception.call_args.args[1],
                                     ns['subprocess'].run.call_args.args[0])

    def test_missing_executable_stops_run(self):
        ns = runner_functions()
        ns['subprocess'].run.side_effect = FileNotFoundError('model executable missing')
        with patch('builtins.print'), self.assertRaises(SystemExit) as error:
            ns['accessibility_calcs']()
        self.assertEqual(error.exception.code, 1)
        self.assertIn('scripts/accessibility/accessibility.py',
                      ns['logger'].exception.call_args.args[1])

    def test_failed_script_arguments_are_logged(self):
        ns = runner_functions()
        ns['subprocess'].run.side_effect = subprocess.CalledProcessError(1, ['skims'])
        with patch('builtins.print'), self.assertRaises(SystemExit):
            ns['build_seed_skims'](10)
        self.assertEqual(ns['logger'].exception.call_args.args[1],
                         [sys.executable, 'scripts/skimming/SkimsAndPaths.py',
                          '-i', '10', 'build_free_flow_skims'])

    def test_success_continues_and_preserves_child_environment(self):
        ns = runner_functions()
        with patch('builtins.print'):
            ns['accessibility_calcs']()
        call = ns['subprocess'].run.call_args
        self.assertTrue(call.kwargs['check'])
        self.assertEqual(call.kwargs['env']['RUN_CONTEXT'], 'chained')
        ns['logger'].exception.assert_not_called()


if __name__ == '__main__':
    unittest.main()
