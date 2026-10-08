"""Check checkout paths without importing licensed model dependencies."""
import ast
from configparser import ConfigParser
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch, mock_open


class ProjectPathTests(unittest.TestCase):
    def load_primary_settings(self, filename, overrides=None):
        source = Path(__file__).resolve().parents[2] / 'input_configuration.py'
        tree = ast.parse(source.read_text())
        nodes = tree.body
        config = ConfigParser(interpolation=None)
        config.read(source.parent / 'local_configuration_template.ini')
        config.set('paths', 'parcels_file_folder', 'custom-parcel-source')
        for section, values in (overrides or {}).items():
            if not config.has_section(section):
                config.add_section(section)
            for name, value in values.items():
                config.set(section, name, value)
        content = io.StringIO()
        config.write(content)
        ns = {'__file__': str(filename)}
        with patch('builtins.open', mock_open(read_data=content.getvalue())):
            exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), ns)
        return ns

    def test_root_follows_configuration_file(self):
        filename = Path.cwd() / 'another checkout' / 'input_configuration.py'
        ns = self.load_primary_settings(filename)
        self.assertEqual(Path(ns['project_folder']), filename.parent.resolve())
        self.assertEqual(Path(ns['daysim_code']), filename.parent / 'daysim_2026')

    def test_parcel_source_can_be_configured_without_editing_code(self):
        ns = self.load_primary_settings(Path.cwd() / 'input_configuration.py')
        self.assertEqual(ns['parcels_file_folder'], 'custom-parcel-source')

    def test_scenario_and_boolean_settings_come_from_ini(self):
        ns = self.load_primary_settings(Path.cwd() / 'input_configuration.py', {
            'scenario': {'base_year': '2025', 'model_year': '2023',
                         'supplemental_module_base_year': '2019', 'scenario_name': 'test',
                         'modeller_initial': 'tester'},
            'paths': {'daysim_code': 'alternate_daysim'},
            'flags': {'run_daysim': 'false', 'include_tnc': 'yes', 'regionwide': 'off'}})
        self.assertEqual(ns['base_year'], '2025')
        self.assertEqual(ns['model_year'], '2023')
        self.assertEqual(ns['supplemental_module_base_year'], '2019')
        self.assertEqual(ns['scenario_name'], 'test')
        self.assertEqual(ns['modeller_initial'], 'tester')
        self.assertEqual(Path(ns['daysim_code']), Path.cwd() / 'alternate_daysim')
        self.assertIs(ns['run_daysim'], False)
        self.assertIs(ns['include_tnc'], True)
        self.assertIs(ns['regionwide'], False)
        self.assertEqual(ns['h5_comparison_file'], 'inputs/model/survey/survey.h5')

    def test_invalid_boolean_is_rejected(self):
        with self.assertRaises(ValueError):
            self.load_primary_settings(Path.cwd() / 'input_configuration.py',
                                       {'flags': {'run_daysim': 'maybe'}})

    def test_every_flag_uses_its_ini_value(self):
        config = ConfigParser(interpolation=None)
        config.read(Path(__file__).resolve().parents[2] / 'local_configuration_template.ini')
        overrides = {name: str(not config.getboolean('flags', name))
                     for name in config.options('flags')}
        ns = self.load_primary_settings(Path.cwd() / 'input_configuration.py',
                                        {'flags': overrides})
        for name in overrides:
            with self.subTest(flag=name):
                self.assertIs(ns[name], not config.getboolean('flags', name))

    def test_absolute_daysim_source_is_preserved(self):
        source = str(Path.cwd() / 'external executables')
        ns = self.load_primary_settings(Path.cwd() / 'input_configuration.py',
                                        {'paths': {'daysim_code': source}})
        self.assertEqual(ns['daysim_code'], source)
