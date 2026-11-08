"""Fetch attributable OSM geometry; normal application startup never uses the network.

    python -m data.fetch_osm harvey_houston
    python -m data.fetch_osm ian_fort_myers --apply

--apply updates anchors only after all requested groups have real nonempty geometry.
Run make_overlays and the scenario/impact checks after applying, before committing.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from shapely.geometry import LineString, Polygon, box, mapping, shape
from shapely.ops import unary_union, linemerge, transform, polygonize

DATA=Path(__file__).resolve().parent
ENDPOINT='https://overpass-api.de/api/interpreter'
ATTRIBUTION='Waterways © OpenStreetMap contributors (ODbL)'
# Query boxes restrict the intended river/coast portions, not the hazard intensity.
GROUPS={
 'harvey_houston':[
  ('Buffalo Bayou','waterway','Buffalo Bayou',(29.70,-95.75,29.86,-95.25)),
  ('Brays Bayou','waterway','Brays Bayou',(29.64,-95.65,29.75,-95.25)),
  ('White Oak Bayou','waterway','White Oak Bayou',(29.74,-95.57,29.88,-95.35)),
  ('Addicks Reservoir','reservoir','Addicks Reservoir',(29.72,-95.80,29.92,-95.55)),
  ('Barker Reservoir','reservoir','Barker Reservoir',(29.64,-95.82,29.84,-95.57)),
 ],
 'ian_fort_myers':[
  ('Caloosahatchee River','waterway','Caloosahatchee River',(26.49,-82.02,26.73,-81.73)),
  ('Gulf coast (Estero Island)','coastline',None,(26.38,-81.99,26.50,-81.84)),
 ]}


def query(kind,name,bounds):
    bbox=','.join(map(str,bounds))
    if kind=='reservoir':
        return f'[out:json][timeout:45];wr["name"={json.dumps(name)}]({bbox});out geom;'
    selector='["natural"="coastline"]' if kind=='coastline' else '["waterway"~"^(river|stream)$"]["name"='+json.dumps(name)+']'
    return f'[out:json][timeout:45];way{selector}({bbox});out geom;'


def fetch(query_text):
    request=Request(ENDPOINT,data=urlencode({'data':query_text}).encode(),headers={'User-Agent':'OperationStorm-HackUTD-geometry/1.0','Content-Type':'application/x-www-form-urlencoded'})
    with urlopen(request,timeout=55) as response:
        if response.status!=200:raise RuntimeError(f'Overpass HTTP {response.status}')
        result=json.load(response)
    if result.get('remark'):raise ValueError('Overpass reported an incomplete response: '+str(result['remark']))
    return result


def _lines(geometry):
    if geometry.geom_type=='LineString':return [geometry]
    if geometry.geom_type in ('MultiLineString','GeometryCollection'):
        return [line for child in geometry.geoms for line in _lines(child)]
    return []


def simplify(line,max_points=150):
    """Use a city-local metric projection, retaining at most max_points vertices."""
    lat=line.centroid.y
    xscale=111320*math.cos(math.radians(lat));yscale=111320
    projected=transform(lambda x,y:(x*xscale,y*yscale),line)
    tolerance=3.0
    result=projected.simplify(tolerance,preserve_topology=False)
    while len(result.coords)>max_points:
        tolerance*=1.8
        result=projected.simplify(tolerance,preserve_topology=False)
    return transform(lambda x,y:(x/xscale,y/yscale),result)


def group_features(response,group_name,bounds):
    if response.get('remark'):raise ValueError('Incomplete Overpass response')
    south,west,north,east=bounds
    window=box(west,south,east,north)
    segments=[];way_ids=[]
    for element in response.get('elements',[]):
        if element.get('type')!='way':continue
        coords=[(p['lon'],p['lat']) for p in element.get('geometry',[]) if 'lat' in p and 'lon' in p]
        if len(coords)<2:continue
        line=LineString(coords)
        if not line.is_valid:raise ValueError('Invalid OSM way geometry')
        clipped=[part for part in _lines(line.intersection(window)) if not part.is_empty and part.length>0]
        if clipped:
            segments.extend(clipped);way_ids.append(element['id'])
    if not segments:raise ValueError(f'No OSM line geometry for {group_name}; keep existing anchors')
    joined=unary_union(segments)
    if joined.geom_type!='LineString':joined=linemerge(joined)
    lines=sorted(_lines(joined),key=lambda line:(line.bounds,-line.length))
    return [{'type':'Feature','geometry':mapping(simplify(line)),'properties':{'anchor_name':group_name,'part':i,'osm_way_ids':sorted(set(way_ids)),'osm_base':response.get('osm3s',{}).get('timestamp_osm_base'),'attribution':ATTRIBUTION}} for i,line in enumerate(lines) if line.length>0]


def reservoir_features(response,group_name,bounds):
    """Assemble only closed OSM rings; no implicit closing of incomplete data."""
    if response.get('remark'):raise ValueError('Incomplete Overpass reservoir response')
    areas=[];references=[]
    for element in response.get('elements',[]):
        if element.get('type')=='way':
            coords=[(point['lon'],point['lat']) for point in element.get('geometry',[])]
            if len(coords)>=4 and coords[0]==coords[-1]:
                polygon=Polygon(coords)
                if not polygon.is_valid:raise ValueError('Invalid reservoir boundary')
                areas.append(polygon);references.append(f"way/{element['id']}")
        elif element.get('type')=='relation':
            rings={'outer':[],'inner':[]}
            for member in element.get('members',[]):
                if member.get('type')!='way' or member.get('role','outer') not in ('outer','inner',''):continue
                coords=[(point['lon'],point['lat']) for point in member.get('geometry',[])]
                if len(coords)>=2:rings[member.get('role') or 'outer'].append(LineString(coords))
            if not rings['outer']:continue
            def area_from_lines(lines):
                if not lines:return None
                merged=unary_union(lines)
                polygons=list(polygonize(merged))
                if not polygons:raise ValueError('Reservoir relation has incomplete rings')
                area=unary_union(polygons)
                # Every fetched segment must be accounted for by a closed ring.
                if merged.difference(area.boundary).length>1e-8:raise ValueError('Reservoir relation has dangling segments')
                return area
            outer=area_from_lines(rings['outer']);inner=area_from_lines(rings['inner'])
            area=outer.difference(inner) if inner is not None else outer
            if not area.is_valid or area.is_empty:raise ValueError('Invalid reservoir multipolygon')
            areas.append(area);references.append(f"relation/{element['id']}")
    if not areas:raise ValueError(f'No closed OSM reservoir geometry for {group_name}')
    south,west,north,east=bounds
    result=unary_union(areas).intersection(box(west,south,east,north))
    if result.is_empty or result.geom_type not in ('Polygon','MultiPolygon'):raise ValueError('Reservoir outside query region')
    # Boundaries are references, not simulated inundation footprints; do not feed them to river buffers.
    return [{'type':'Feature','geometry':mapping(result),'properties':{'anchor_name':group_name,'role':'reservoir_reference','osm_references':sorted(set(references)),'osm_base':response.get('osm3s',{}).get('timestamp_osm_base'),'attribution':ATTRIBUTION,'reference_only':True}}]


def snapshot(scenario,fetcher=fetch):
    features=[]
    for group,kind,name,bounds in GROUPS[scenario]:
        response=fetcher(query(kind,name,bounds))
        features.extend(reservoir_features(response,group,bounds) if kind=='reservoir' else group_features(response,group,bounds))
    return {'type':'FeatureCollection','properties':{'scenario_id':scenario,'endpoint':ENDPOINT,'retrieved_at':datetime.now(timezone.utc).isoformat(),'attribution':ATTRIBUTION,'license':'https://www.openstreetmap.org/copyright','note':'Real base geometry; hazard widths and depths remain synthetic, not official flood zones.'},'features':features}


def apply_snapshot(anchor,snapshot_data):
    """Build new anchor data without mutating input or bridging disconnected waterways."""
    anchor=json.loads(json.dumps(anchor))
    templates={r.get('osm_group',r['name']):r for r in anchor['rivers']}
    grouped={name:[] for name in templates}
    for feature in snapshot_data['features']:
        name=feature['properties']['anchor_name']
        if name in grouped:
            line=shape(feature['geometry'])
            if line.geom_type!='LineString' or line.is_empty or not line.is_valid or len(line.coords)>150:raise ValueError('Invalid snapshot line')
            grouped[name].append(feature)
    if any(not features for features in grouped.values()):raise ValueError('Snapshot is missing required waterways; anchors unchanged')
    rivers=[]
    for name,features in grouped.items():
        for feature in features:
            original=templates[name]
            rivers.append({**original,'name':name,'osm_group':name,'coords':feature['geometry']['coordinates']})
    anchor['rivers']=rivers
    anchor['sources']=list(dict.fromkeys(anchor.get('sources',[])+[ATTRIBUTION]))
    note='River/coast coords derived from the committed OSM snapshot; hazard widths/depths remain illustrative.'
    if note not in anchor.get('_comment',''):anchor['_comment']=(anchor.get('_comment','')+' '+note).strip()
    # Reservoir-release pools remain synthetic; do not relabel hand-placed reservoir areas as OSM data.
    return anchor


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('scenarios',nargs='*',choices=list(GROUPS));parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    for scenario in args.scenarios or list(GROUPS):
        result=snapshot(scenario)
        anchor_path=DATA/'anchors'/f'{scenario}.json'
        updated=apply_snapshot(json.loads(anchor_path.read_text()),result) if args.apply else None
        target=DATA/'osm'/f'{scenario}.geojson';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
        if updated:anchor_path.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+'\n')
        print(f'Saved {target.name}: {len(result["features"])} attributable geometry features'+('; anchors updated, regenerate and validate overlays next' if updated else '; anchors unchanged'))


if __name__=='__main__':main()
