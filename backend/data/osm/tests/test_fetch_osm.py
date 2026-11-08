"""Synthetic unit fixtures only; none of these coordinates are claimed as fetched OSM."""
import json
import unittest
from shapely.geometry import LineString
from data.fetch_osm import group_features, simplify, apply_snapshot, query, snapshot
BOUNDS=(0,0,3,3)
def response():return {'osm3s':{'timestamp_osm_base':'2026-11-08T00:00:00Z'},'elements':[{'type':'way','id':1,'geometry':[{'lon':0,'lat':1},{'lon':1,'lat':1}]},{'type':'way','id':2,'geometry':[{'lon':1,'lat':1},{'lon':2,'lat':1}]}]}
class Geometry(unittest.TestCase):
    def test_merge_and_provenance(self):
        features=group_features(response(),'river',BOUNDS)
        self.assertEqual(len(features),1);self.assertEqual(features[0]['properties']['osm_way_ids'],[1,2]);self.assertEqual(features[0]['geometry']['type'],'LineString')
    def test_disconnected_parts_not_bridged(self):
        r=response();r['elements'][1]['geometry']=[{'lon':2,'lat':1},{'lon':3,'lat':1}]
        self.assertEqual(len(group_features(r,'river',BOUNDS)),2)
    def test_clipping(self):
        r=response();r['elements'][0]['geometry'][0]['lon']=-100
        f=group_features(r,'river',BOUNDS)
        self.assertTrue(all(0<=point[0]<=3 for feat in f for point in feat['geometry']['coordinates']))
    def test_vertex_budget(self):
        import math
        line=LineString([(i*.0001,29+math.sin(i)*.0001) for i in range(2000)])
        self.assertLessEqual(len(simplify(line).coords),150)
    def test_reapply_is_idempotent(self):
        a={'rivers':[{'name':'river','coords':[[0,0],[1,1]],'peak_ft':8,'half_width_mi':.5}]}
        data={'features':group_features(response(),'river',BOUNDS)}
        first=apply_snapshot(a,data)
        self.assertEqual(first,apply_snapshot(first,data))
    def test_empty_is_error(self):
        with self.assertRaises(ValueError):group_features({'elements':[]},'river',BOUNDS)
    def test_incomplete_is_error(self):
        with self.assertRaises(ValueError):group_features(response()|{'remark':'timeout'},'river',BOUNDS)
    def test_apply_requires_all_groups_and_preserves_hazard_constants(self):
        a={'rivers':[{'name':'river','coords':[[0,0],[1,1]],'peak_ft':8,'half_width_mi':.5}],'pools':[{'name':'synthetic reservoir'}]}
        data={'features':group_features(response(),'river',BOUNDS)}
        updated=apply_snapshot(a,data)
        self.assertEqual(updated['rivers'][0]['peak_ft'],8);self.assertEqual(updated['pools'],a['pools']);self.assertNotIn('sources',a)
        with self.assertRaises(ValueError):apply_snapshot(a,{'features':[]})
    def test_all_groups_fetched_before_snapshot_return(self):
        seen=[]
        def fake(q):
            import re
            seen.append(q)
            south,west,north,east=map(float,re.search(r'\(([-\d.,]+)\);out',q).group(1).split(','))
            return {'elements':[{'type':'way','id':1,'geometry':[{'lon':west+.01,'lat':south+.01},{'lon':east-.01,'lat':north-.01}]}]}
        result=snapshot('harvey_houston',fake)
        self.assertEqual(len(seen),3);self.assertEqual(len(result['features']),3)
    def test_query_contains_named_waterway_and_geometry(self):
        q=query('waterway','Buffalo Bayou',BOUNDS)
        self.assertIn('Buffalo Bayou',q);self.assertIn('out geom',q)
if __name__=='__main__':unittest.main()
