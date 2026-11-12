"""Beijing pilot. Key via AMAP_KEY environment only. Run with python -I.
Dependencies: requests, pyshp, shapely. No automatic retries; max 1520 requests.
Building representative points are NOT verified entrances. OSM © contributors, ODbL.
"""
import argparse, csv, json, math, os, time
from datetime import datetime, timezone
from pathlib import Path
import requests

MODES = {'walking':'walking', 'cycling':'bicycling', 'driving':'driving', 'transit':'transit/integrated'}

def gcj(lon, lat):
    x,y=lon-105,lat-35
    a=-100+2*x+3*y+.2*y*y+.1*x*y+.2*math.sqrt(abs(x))
    a+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
    a+=(20*math.sin(y*math.pi)+40*math.sin(y/3*math.pi))*2/3
    a+=(160*math.sin(y/12*math.pi)+320*math.sin(y*math.pi/30))*2/3
    b=300+x+2*y+.1*x*x+.1*x*y+.1*math.sqrt(abs(x))
    b+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
    b+=(20*math.sin(x*math.pi)+40*math.sin(x/3*math.pi))*2/3
    b+=(150*math.sin(x/12*math.pi)+300*math.sin(x/30*math.pi))*2/3
    rad=lat/180*math.pi; magic=1-.006693421622965943*math.sin(rad)**2
    return lon+b*180/(6378245/math.sqrt(magic)*math.cos(rad)*math.pi),lat+a*180/((6378245*(1-.006693421622965943))/(magic*math.sqrt(magic))*math.pi)

def prepare(src, out):
    import shapefile
    from shapely.geometry import shape, box
    r=shapefile.Reader(str(Path(src)/'gis_osm_buildings_a_free_1.shp'), encoding='utf-8')
    candidates=[]; region=box(116.36,39.89,116.44,39.95)
    for sr in r.iterShapeRecords():
        bb=sr.shape.bbox
        if bb[2]<116.36 or bb[0]>116.44 or bb[3]<39.89 or bb[1]>39.95: continue
        try:
            g=shape(sr.shape.__geo_interface__)
            if not g.is_valid or g.is_empty: continue
            p=g.representative_point()
            if not region.contains(p): continue
            rec=sr.record.as_dict()
            candidates.append((p.x,p.y,rec))
        except (ValueError,TypeError): continue
    # One building nearest each fixed grid-cell center; spatially spread, reproducible.
    chosen=[]; used=set()
    for iy in range(4):
        for ix in range(5):
            target=(116.36+(ix+.5)*.08/5,39.89+(iy+.5)*.06/4)
            ranked=sorted(range(len(candidates)),key=lambda k: ((candidates[k][0]-target[0])*.77)**2+(candidates[k][1]-target[1])**2)
            k=next(k for k in ranked if k not in used);used.add(k)
            x,y,rec=candidates[k];gx,gy=gcj(x,y)
            chosen.append(dict(node_id=f'b{len(chosen)+1:03}',source_id=rec.get('osm_id',''),name=rec.get('name',''),lon_wgs84=x,lat_wgs84=y,lon=round(gx,6),lat=round(gy,6),coord_system='GCJ-02_approx',point_method='interior_representative_not_entrance'))
    out.mkdir(parents=True,exist_ok=True)
    with (out/'nodes.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=chosen[0]);w.writeheader();w.writerows(chosen)
    (out/'metadata.json').write_text(json.dumps(dict(source='OpenStreetMap contributors / Geofabrik',source_snapshot='2026-01-01T21:21:30Z',license='ODbL 1.0',bbox_wgs84=[116.36,39.89,116.44,39.95],sampling='5x4 grid nearest building representative point',coordinate_conversion='local approximate WGS84 to GCJ02; not official conversion service; entrance and snapping not validated',transit='public transport, not pure metro',route_selection='minimum positive duration among returned candidates',time_context='live query time, not synchronized departure; do not label as peak-hour snapshot'),ensure_ascii=False,indent=2))
    print('Prepared',len(chosen),'nodes from',len(candidates),'candidates')

def collect(out,limit):
    key=os.environ.get('AMAP_KEY')
    if not key: raise SystemExit('Set AMAP_KEY; never commit your key')
    nodes=list(csv.DictReader((out/'nodes.csv').open()))
    raw=out/'responses.jsonl';existing=[]
    if raw.exists(): existing=[json.loads(s) for s in raw.read_text().splitlines() if s.strip()]
    done={(x['origin_id'],x['destination_id'],x['mode']) for x in existing}
    attempts=0; session=requests.Session()
    # Interleave modes and directions to test each API before full collection.
    for i in nodes:
      for j in nodes:
       if i['node_id']==j['node_id']: continue
       for mode,endpoint in MODES.items():
        if (i['node_id'],j['node_id'],mode) in done: continue
        if attempts>=limit: return
        params={'key':key,'origin':f"{i['lon']},{i['lat']}",'destination':f"{j['lon']},{j['lat']}",'show_fields':'cost,polyline'}
        if mode=='transit': params.update(city1='010',city2='010',strategy='0')
        row=dict(origin_id=i['node_id'],destination_id=j['node_id'],mode=mode,requested_at=datetime.now(timezone.utc).isoformat(),endpoint=endpoint,strategy=params.get('strategy','default'))
        attempts+=1
        try:
            response=session.get('https://restapi.amap.com/v5/direction/'+endpoint,params=params,timeout=25)
            row['http_status']=response.status_code
            payload=response.json();row['response']=payload
            row['status']='api_success' if payload.get('status')=='1' else 'api_error'
        except Exception as e:
            row['status']='transport_error';row['error_type']=type(e).__name__
        with raw.open('a') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
        payload=row.get('response',{})
        print(attempts,mode,row['status'],payload.get('infocode',''),flush=True)
        # Stop on any API/transport error: no unauthorized retries or repeated invalid calls.
        if row['status']!='api_success' and payload.get('infocode')!='20803':
            print('STOP: inspect saved response before continuing',flush=True);return
        time.sleep(.08)

def export(out):
    records=[json.loads(s) for s in (out/'responses.jsonl').read_text().splitlines() if s.strip()]
    edges=[]
    for r in records:
        row={k:r[k] for k in ['origin_id','destination_id','mode','requested_at','strategy']}
        row.update(status=r['status'],duration_s='',distance_m='',route_rank='',error_code=r.get('response',{}).get('infocode',''))
        p=r.get('response',{});routes=p.get('route',{})
        if not isinstance(routes,dict): routes={}
        candidates=routes.get('transits' if r['mode']=='transit' else 'paths',[]) or []
        valid=[]
        for k,c in enumerate(candidates):
            cost=c.get('cost',{})
            try:
                t=float(cost.get('duration',c.get('duration')))
                if t>0: valid.append((t,k,c))
            except (TypeError,ValueError): pass
        if valid:
            t,k,c=min(valid,key=lambda v:v[0]);row.update(status='ok',duration_s=t,distance_m=c.get('distance',''),route_rank=k)
        elif row['status']=='api_success': row['status']='no_duration_or_no_route'
        edges.append(row)
    with (out/'edges.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=edges[0]);w.writeheader();w.writerows(edges)
    summary={m:{'attempts':sum(e['mode']==m for e in edges),'ok':sum(e['mode']==m and e['status']=='ok' for e in edges)} for m in MODES}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','collect','export']);p.add_argument('--out',required=True);p.add_argument('--source');p.add_argument('--limit',type=int,default=4);a=p.parse_args();out=Path(a.out)
    if a.action=='prepare': prepare(a.source,out)
    elif a.action=='collect': collect(out,max(0,min(a.limit,9800)))
    else: export(out)
