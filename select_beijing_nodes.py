"""Purposeful functional sample, not population representative. AMAP_KEY via env."""
import os,json,csv,time,argparse
from pathlib import Path
from datetime import datetime,timezone
import requests
GROUPS={
'就业商务':['北京中关村软件园','北京中关村壹号','北京国贸商城','北京金融街购物中心','北京望京SOHO','北京丽泽SOHO','北京亦庄经济技术开发区管委会','北京丰台科技园创新中心','北京首钢园','北京未来科学城展示中心'],
'交通枢纽':['北京站','北京南站','北京西站','北京北站','北京朝阳站','北京丰台站','北京清河站','北京首都国际机场T3航站楼','北京大兴国际机场航站楼','北京东直门交通枢纽'],
'教育医疗':['北京大学','清华大学','中国人民大学','北京师范大学','北京工业大学','首都医科大学附属北京天坛医院','北京协和医院东院','北京大学第三医院','中日友好医院','首都医科大学附属北京儿童医院'],
'商业文化':['北京王府井百货大楼','北京三里屯太古里','北京西单大悦城','北京合生汇','北京五棵松华熙LIVE','北京国家图书馆','北京中国国家博物馆','北京国家大剧院','北京奥林匹克森林公园南门','北京环球城市大道'],
'居住片区代表设施':['北京回龙观体育文化公园','北京天通苑文化艺术中心','北京望京文化体育公园','北京方庄体育公园','北京劲松街道办事处','北京双井街道办事处','北京通州梨园街道办事处','北京大兴黄村镇人民政府','北京石景山鲁谷街道办事处','北京海淀清河街道办事处']}
def run(out):
 out.mkdir(exist_ok=True,parents=True);raw=out/'poi_queries.jsonl';old={}
 if raw.exists():old={r['query']:r for r in map(json.loads,raw.read_text().splitlines())}
 key=os.environ['AMAP_KEY'];selected=[];review=[];seen=set()
 for group,queries in GROUPS.items():
  for query in queries:
   if query not in old:
    try:
     p=requests.get('https://restapi.amap.com/v5/place/text',params={'key':key,'keywords':query,'region':'北京市','city_limit':'true','page_size':5},timeout=25).json()
    except Exception as e:print(type(e).__name__);return
    r={'query':query,'requested_at':datetime.now(timezone.utc).isoformat(),'response':p}
    with raw.open('a') as f:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    old[query]=r;time.sleep(.15)
   r=old[query];p=r['response']
   if p.get('status')!='1':print('STOP',p.get('infocode'),p.get('info'));return
   candidates=[c for c in p.get('pois',[]) if str(c.get('adcode','')).startswith('11') and c.get('location') and c['id'] not in seen]
   if not candidates:review.append({'query':query,'issue':'no Beijing candidate'});continue
   # API relevance order; explicit review record, not a claim of exact match.
   c=candidates[0];seen.add(c['id']);lon,lat=c['location'].split(',')
   selected.append(dict(node_id=f'n{len(selected)+1:03}',functional_group=group,search_query=query,poi_id=c['id'],name=c['name'],lon_gcj02=lon,lat_gcj02=lat,address=c.get('address',''),district=c.get('adname',''),adcode=c.get('adcode',''),poi_type=c.get('type',''),selection_rule='first Beijing candidate in API relevance order; manually review',entrance_verified=False,requested_at=r['requested_at']))
   review.append({'query':query,'selected':c['name'],'alternatives':[{'id':v['id'],'name':v['name'],'address':v.get('address')} for v in candidates]})
 with (out/'nodes_50.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=selected[0]);w.writeheader();w.writerows(selected)
 (out/'match_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2));print('selected',len(selected));print('\n'.join(f"{n['node_id']} {n['search_query']} => {n['name']} ({n['district']})" for n in selected))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();run(Path(a.out))
