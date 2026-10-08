"""Validate external Daysim populations before publishing model inputs."""
from pathlib import Path
import numpy as np
import pandas as pd

# DO NOT change the order of these columns; they are used to validate the order of columns in the input files
HOUSEHOLD_COLUMNS = tuple('hhno hhsize hhvehs hhwkrs hhftw hhptw hhret hhoad hhuni hhhsc hh515 hhcu5 hhincome hownrent hrestype hhparcel hhtaz hhexpfac samptype'.split())
PERSON_COLUMNS = tuple('hhno pno pptyp pagey pgend pwtyp pwpcl pwtaz pwautime pwaudist pstyp pspcl pstaz psautime psaudist puwmode puwarrp puwdepp ptpass ppaidprk pdiary pproxy psexpfac'.split())


def load_population(folder):
    """Return raw frames and file-reading errors without validating data."""
    errors = []
    frames = {}
    for filename in ('_household.tsv', '_person.tsv'):
        path = Path(folder) / filename
        try:
            # Read the header separately: pandas otherwise renames duplicate columns.
            with open(path, encoding='utf-8-sig') as source:
                header = source.readline().rstrip('\r\n').split('\t')
            frame = pd.read_csv(path, sep='\t')
            frame.attrs['source_columns'] = header
        except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as error:
            errors.append(f'{filename}: {error}')
            continue
        frames[filename] = frame
    return frames, errors


def validate_population(frames):
    """Return data errors; normalize numeric columns in the supplied frames.

    File-loading errors are collected separately by load_population.
    """
    errors = []
    valid_frames = {}
    for filename, columns, extra in (
            ('_household.tsv', HOUSEHOLD_COLUMNS, ('zone_id', 'fraction_with_jobs_outside')),
            ('_person.tsv', PERSON_COLUMNS, ('id',))):
        frame = frames.get(filename)
        if frame is None:
            continue
        header = frame.attrs.get('source_columns', list(frame.columns))
        if len(header) != len(set(header)):
            errors.append(f'{filename}: duplicate column names')
        missing = sorted(set(columns + extra) - set(frame.columns))
        if missing:
            errors.append(f'{filename}: missing columns {", ".join(missing)}')
        if frame.empty:
            errors.append(f'{filename}: no data rows')
        valid = True
        for column in columns + extra:
            if column not in frame:
                valid = False
                continue
            numeric = pd.to_numeric(frame[column], errors='coerce')
            if not np.isfinite(numeric).all():
                errors.append(f'{filename}: {column} must contain finite numeric values')
                valid = False
                continue
            fractional = column.endswith('expfac') or column in (
                'fraction_with_jobs_outside', 'pwautime', 'pwaudist', 'psautime', 'psaudist')
            if not fractional and (numeric % 1 != 0).any():
                errors.append(f'{filename}: {column} must contain integer values')
                valid = False
            frame[column] = numeric
        if valid:
            valid_frames[filename] = frame
    households = valid_frames.get('_household.tsv')
    persons = valid_frames.get('_person.tsv')
    if households is not None:
        if households['hhno'].duplicated().any():
            errors.append('_household.tsv: duplicate hhno')
        for column in ('hhno', 'hhsize', 'hhparcel'):
            if (households[column] <= 0).any():
                errors.append(f'_household.tsv: {column} must be positive')
        if (households['hhexpfac'] < 0).any():
            errors.append('_household.tsv: hhexpfac must be nonnegative')
    if persons is not None:
        if persons.duplicated(['hhno', 'pno']).any():
            errors.append('_person.tsv: duplicate (hhno, pno)')
        if persons['id'].duplicated().any():
            errors.append('_person.tsv: duplicate id')
        if (persons[['hhno', 'pno']] <= 0).any().any():
            errors.append('_person.tsv: hhno and pno must be positive')
        if (persons['psexpfac'] < 0).any():
            errors.append('_person.tsv: psexpfac must be nonnegative')
    if households is not None and persons is not None:
        if not persons['hhno'].isin(households['hhno']).all():
            errors.append('_person.tsv: references an unknown household')
        counts = persons.groupby('hhno').size()
        if (households['hhno'].map(counts).fillna(0) != households['hhsize']).any():
            errors.append('_household.tsv: hhsize does not match person counts')
    return errors
