"""Numerical regressions without importing licensed Emme modules."""
import ast
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

def main_nodes(filename):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8-sig'))
    return next(n.body for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')

def execute(nodes, namespace):
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<model calculation>', 'exec'), namespace)
    return namespace

def has_name(node, name):
    return any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(node))

class GenerationTests(unittest.TestCase):
    def balance(self, frame):
        tree = ast.parse((ROOT/'scripts/supplemental/generation.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'balance_supplemental_trips')
        ns = execute([node], dict(np=np, pd=pd))
        return ns[node.name](frame, ['hsp'], 'pro')

    def test_positive_productions_with_zero_attractions_fail(self):
        with self.assertRaisesRegex(ValueError, 'hsp'):
            self.balance(pd.DataFrame({'hsppro':[10.], 'hspatt':[0.]}))

    def test_invalid_trip_values_fail(self):
        for value in [float('nan'), float('inf'), -1.]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.balance(pd.DataFrame({'hsppro':[10.], 'hspatt':[value]}))

    def test_valid_balance_preserves_distribution(self):
        result = self.balance(pd.DataFrame({'hsppro':[12., 8.], 'hspatt':[1., 3.]}))
        np.testing.assert_allclose(result.hspatt, [5., 15.])
        result = self.balance(pd.DataFrame({'hsppro':[0.], 'hspatt':[0.]}))
        self.assertEqual(result.hspatt.sum(), 0.)

    def test_group_quarters_accumulate_all_categories(self):
        nodes = main_nodes('scripts/supplemental/generation.py')
        loop = next(n for n in nodes if isinstance(n, ast.For) and has_name(n, 'gq_type'))
        ns = execute([loop], dict(trip_productions=['hsppro'],
            total_gq_df=pd.DataFrame({'dorms':[10.], 'military':[20.], 'other':[30.]}),
            df_gq_rates=pd.DataFrame({'segmentation':['dorms','military','other'], 'hsppro':[1.,2.,3.]})))
        self.assertEqual(ns['total_gq_df'].hsppro.iloc[0], 140.)

    def test_college_rates_match_college_class(self):
        node = next(n for n in main_nodes('scripts/supplemental/generation.py')
                    if isinstance(n, ast.Assign) and has_name(n, 'df_coll_rates') and has_name(n, 'df_hh')
                    and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                    and n.value.func.attr == 'merge')
        ns = execute([node], dict(pd=pd,
            df_hh=pd.DataFrame({'si':['s0i1'], 'ci':['c1i1']}),
            df_coll_rates=pd.DataFrame({'segmentation':['c1i1'], 'colpro':[2.]})))
        self.assertEqual(ns['df_hh'].colpro.iloc[0], 2.)

    def test_missing_college_class_fails(self):
        nodes = main_nodes('scripts/supplemental/generation.py')
        start = next(i for i,n in enumerate(nodes) if isinstance(n,ast.Assign)
                     and isinstance(n.targets[0],ast.Name) and n.targets[0].id == 'missing_college_classes')
        with self.assertRaisesRegex(ValueError, 'c2i1'):
            execute(nodes[start:start+2], dict(pd=pd,
                df_hh=pd.DataFrame({'ci':['c2i1']}),
                df_coll_rates=pd.DataFrame({'segmentation':['c1i1'], 'colpro':[2.]})))

    def test_i5_adjustment_updates_each_purpose(self):
        loops = [n for n in main_nodes('scripts/supplemental/generation.py')
                 if isinstance(n, ast.For) and has_name(n, 'revised_external_taz') and has_name(n, 'i5_station')]
        original = pd.DataFrame({'aapro':[30.], 'bbpro':[70.], 'aaatt':[40.], 'bbatt':[60.], 'wtopro':[9.]}, index=[1511])
        ns = execute(loops, dict(trip_productions=['aapro','bbpro'], trip_attractions=['aaatt','bbatt'],
            revised_external_taz=original.copy(), i5_station=1511, purpose='wtopro',
            i5_ext_productions=100., i5_ext_attractions=100.,
            i5_revised_productions=80., i5_revised_attractions=50.))
        np.testing.assert_allclose(ns['revised_external_taz'].loc[1511], [24.,56.,20.,30.,9.])

    def test_distribution_aligns_nonconsecutive_zone_ids(self):
        nodes = main_nodes('scripts/supplemental/distribute_non_work_ixxi.py')
        start = next(i for i,n in enumerate(nodes) if isinstance(n, ast.Assign) and has_name(n, 'zones_df'))
        stop = next(i for i in range(start+1,len(nodes)) if has_name(nodes[i], 'load_skims'))
        project = type('Project', (), {'current_scenario':type('Scenario', (), {'zone_numbers':[10,30,20]})()})()
        ns = execute(nodes[start:stop], dict(pd=pd,my_project=project,
            trip_table=pd.DataFrame({'BKRCastTAZ':[20,10,30], 'hspatt':[2.,1.,3.]}).set_index('BKRCastTAZ')))
        np.testing.assert_allclose(ns['trip_table'].hspatt.reindex([10,30,20]), [1.,3.,2.])

if __name__ == '__main__':
    unittest.main()
