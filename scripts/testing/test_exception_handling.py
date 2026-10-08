"""Exercise failure handling without importing licensed dependencies."""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock


def function_namespace(filename, name, **namespace):
    source = Path(__file__).resolve().parents[2] / filename
    tree = ast.parse(source.read_text())
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace


class ExceptionHandlingTests(unittest.TestCase):
    def test_network_attribute_error_is_not_replaced_with_zero(self):
        link = Mock()
        link.__getitem__ = Mock(side_effect=KeyError('missing volume'))
        network = Mock()
        network.attributes.return_value = ['volume']
        network.modes.return_value = []
        network.links.return_value = [link]
        ns = function_namespace('scripts/summarize/standard/network_summary.py',
                                'export_network_attributes', logger=Mock())
        with self.assertRaises(KeyError):
            ns['export_network_attributes'](network, None)

    def test_git_failure_is_logged(self):
        import subprocess
        subprocess_mock = Mock()
        subprocess_mock.CalledProcessError = subprocess.CalledProcessError
        subprocess_mock.check_output.side_effect = FileNotFoundError('git missing')
        logging = Mock()
        ns = function_namespace('scripts/data_wrangling.py', 'get_current_commit_hash',
                                subprocess=subprocess_mock, logging=logging)
        ns['get_current_commit_hash']()
        logging.getLogger.return_value.warning.assert_called_once()


class ExplicitImportTests(unittest.TestCase):
    def test_core_modules_have_no_wildcard_imports(self):
        root = Path(__file__).resolve().parents[2]
        for filename in ('run_bkrcast.py', 'scripts/data_wrangling.py', 'scripts/logcontroller.py'):
            with self.subTest(filename=filename):
                tree = ast.parse((root / filename).read_text())
                self.assertFalse(any(isinstance(node, ast.ImportFrom) and
                                     any(alias.name == '*' for alias in node.names)
                                     for node in ast.walk(tree)))


class ResourceCleanupTests(unittest.TestCase):
    def test_population_hdf5_closes_when_conversion_fails(self):
        import os
        from unittest.mock import MagicMock
        handle = MagicMock()
        handle.__enter__.return_value = handle
        ns = function_namespace('scripts/data_wrangling.py', 'get_hhs_df_from_synpop',
                                os=os, project_folder='project', households_persons_file='population.h5',
                                h5py=Mock(File=Mock(return_value=handle)),
                                h5_to_df=Mock(side_effect=ValueError('bad dataset')))
        with self.assertRaises(ValueError):
            ns['get_hhs_df_from_synpop']()
        handle.__exit__.assert_called_once()

    def test_bike_hdf5_closes_when_matrix_conversion_fails(self):
        from unittest.mock import MagicMock
        handle = MagicMock()
        handle.__enter__.return_value = handle
        project = Mock()
        project.emmeMatrix_to_numpyMatrix.side_effect = ValueError('bad matrix')
        ns = function_namespace('scripts/bikes/bike_model.py', 'export_skims',
                                h5py=Mock(File=Mock(return_value=handle)), logger=Mock())
        with self.assertRaises(ValueError):
            ns['export_skims'](project, 'bike', '6to9')
        handle.__exit__.assert_called_once()


    def test_emmebank_disposed_when_scenario_creation_fails(self):
        bank = Mock()
        bank.create_scenario.side_effect = RuntimeError('scenario failed')
        os_mock = Mock()
        os_mock.path.join.side_effect = lambda *parts: '/'.join(parts)
        os_mock.path.exists.return_value = False
        ns = function_namespace('scripts/summarize/standard/daily_bank.py', 'create_emmebank',
                                os=os_mock, shutil=Mock(), json_to_dictionary=Mock(return_value={}),
                                _emmebank=Mock(create=Mock(return_value=bank)))
        with self.assertRaises(RuntimeError):
            ns['create_emmebank']('Daily')
        bank.dispose.assert_called_once()
