import tempfile
from pathlib import Path
import unittest
import pandas as pd
from scripts.utils.synthetic_population import load_population, validate_population, HOUSEHOLD_COLUMNS, PERSON_COLUMNS


class PopulationTests(unittest.TestCase):
    def fixtures(self, directory):
        households = dict.fromkeys(HOUSEHOLD_COLUMNS, 0)
        households.update(hhno=1, hhsize=1, hhparcel=123, hhexpfac=1)
        households.update(zone_id=1, fraction_with_jobs_outside=0)
        persons = dict.fromkeys(PERSON_COLUMNS, 0)
        persons.update(hhno=1, pno=1, psexpfac=1, id=1)
        pd.DataFrame([households]).to_csv(Path(directory) / '_household.tsv', sep='\t', index=False)
        pd.DataFrame([persons]).to_csv(Path(directory) / '_person.tsv', sep='\t', index=False)

    def test_missing_files_reported_together(self):
        with tempfile.TemporaryDirectory() as directory:
            frames, errors = load_population(directory)
            self.assertFalse(frames)
            self.assertIn('_household.tsv', '\n'.join(errors))
            self.assertIn('_person.tsv', '\n'.join(errors))

    def test_valid_population_has_explicit_daysim_order(self):
        with tempfile.TemporaryDirectory() as directory:
            self.fixtures(directory)
            frames, errors = load_population(directory)
            self.assertFalse(errors)
            self.assertFalse(validate_population(frames))
            households = frames['_household.tsv'].loc[:, HOUSEHOLD_COLUMNS]
            persons = frames['_person.tsv'].loc[:, PERSON_COLUMNS]
            self.assertEqual(list(households.columns), list(HOUSEHOLD_COLUMNS))
            self.assertEqual(households.columns[15], 'hhparcel')
            self.assertEqual(list(persons.columns), list(PERSON_COLUMNS))

    def test_duplicate_orphan_and_size_errors_reported_together(self):
        with tempfile.TemporaryDirectory() as directory:
            self.fixtures(directory)
            path = Path(directory) / '_person.tsv'
            persons = pd.read_csv(path, sep='\t')
            persons['hhno'] = 99
            pd.concat([persons, persons]).to_csv(path, sep='\t', index=False)
            frames, errors = load_population(directory)
            self.assertFalse(errors)
            errors = validate_population(frames)
            for message in ('duplicate', 'unknown household', 'hhsize'):
                self.assertIn(message, '\n'.join(errors))

    def test_invalid_numeric_value_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.fixtures(directory)
            path = Path(directory) / '_household.tsv'
            households = pd.read_csv(path, sep='\t')
            households['hhparcel'] = 'invalid'
            households.to_csv(path, sep='\t', index=False)
            frames, errors = load_population(directory)
            self.assertFalse(errors)
            self.assertEqual(frames['_household.tsv']['hhparcel'].iloc[0], 'invalid')
            self.assertIn('hhparcel', '\n'.join(validate_population(frames)))
