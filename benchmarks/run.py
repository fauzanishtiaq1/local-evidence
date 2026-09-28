"""Independent reproducible benchmark for local-evidence."""
import argparse,json,statistics,subprocess,sys,tempfile,time,hashlib,platform
from pathlib import Path
HERE=Path(__file__).parents[1]; EX=HERE/'examples'
def scan(root,query):
 terms=query.casefold().split(); hits=[]
 for p in sorted(root.rglob('*')):
  if p.is_file() and p.suffix in {'.md','.txt','.rst'}:
   lines=p.read_text(encoding='utf-8').splitlines()
   if all(any(term in line.casefold() for line in lines) for term in terms): hits.append(p.relative_to(root).as_posix())
 return hits
def pct(xs,q): return sorted(xs)[min(len(xs)-1,int((len(xs)-1)*q))]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output',required=True); a=ap.parse_args(); manifest=json.loads((EX/'manifest.json').read_text(encoding='utf-8'))
 with tempfile.TemporaryDirectory() as td:
  idx=Path(td)/'index'; t=time.perf_counter(); b=subprocess.run([sys.executable,'-m','local_evidence','build',str(EX),str(idx)],cwd=HERE,text=True,capture_output=True); build_s=time.perf_counter()-t
  if b.returncode: raise SystemExit(b.stderr)
  recall=[]; mrr=[]; lat=[]; exact=True; raw_queries=[]; baseline_recall=[]; baseline_mrr=[]
  for item in manifest['queries']:
   expected=set(item['relevant']); baseline_started=time.perf_counter(); baseline=scan(EX,item['query']); baseline_seconds=time.perf_counter()-baseline_started
   if not baseline: raise SystemExit('empty independent baseline')
   times=[]; reference=None
   for _ in range(20):
    t=time.perf_counter(); r=subprocess.run([sys.executable,'-m','local_evidence','search',str(idx),item['query'],'--top-k','5'],cwd=HERE,text=True,capture_output=True,encoding='utf-8'); times.append(time.perf_counter()-t)
    if r.returncode: raise SystemExit(r.stderr)
    hits=json.loads(r.stdout)
    if reference is None: reference=hits
    if hits != reference: raise SystemExit('nondeterministic search output')
    for hit in hits:
     source=(EX/hit['path']).read_text(encoding='utf-8'); lines=source.splitlines()
     if not 1 <= hit['start_line'] <= hit['end_line'] <= len(lines): raise SystemExit('invalid citation range')
     if hit['text'] != '\n'.join(lines[hit['start_line']-1:hit['end_line']]): raise SystemExit('citation text mismatch')
     if hit['source_sha256'] != hashlib.sha256(source.encode('utf-8')).hexdigest(): raise SystemExit('source hash mismatch')
   lat.extend(times)
   paths=[h['path'] for h in hits]; recall.append(len(set(paths[:5])&expected)/len(expected)); mrr.append(next((1/(i+1) for i,p in enumerate(paths[:5]) if p in expected),0)); exact &= bool(hits) and hits[0]['path'] in expected
   baseline_recall.append(len(set(baseline[:5])&expected)/len(expected));baseline_mrr.append(next((1/(i+1) for i,p in enumerate(baseline[:5]) if p in expected),0))
   raw_queries.append({'query':item['query'],'expected':sorted(expected),'ranked_paths':paths,'process_seconds':times,'baseline_paths':baseline,'baseline_inprocess_seconds':baseline_seconds})
  stats=json.loads(subprocess.run([sys.executable,'-m','local_evidence','stats',str(idx)],cwd=HERE,text=True,capture_output=True).stdout); result={'benchmark':'synthetic-authored-corpus','queries':len(manifest['queries']),'repeated_process_searches':len(lat),'groundtruth_citation_exact':exact,'recall_at_5':statistics.mean(recall),'mrr_at_5':statistics.mean(mrr),'baseline_matching_files':{x['query']:scan(EX,x['query']) for x in manifest['queries']},'build_seconds':build_s,'cold_search_median_seconds':statistics.median(lat),'cold_search_p95_seconds':pct(lat,.95),'index_bytes':stats['bytes'],'index_stats':stats,'python':sys.version,'platform':sys.platform}
  result.update({'raw_queries':raw_queries,'baseline_recall_at_5':statistics.mean(baseline_recall),'baseline_mrr_at_5':statistics.mean(baseline_mrr),'machine':platform.machine(),'limits':['Small authored synthetic corpus; no external validity or human-time claim.','Cold means fresh Python process, not flushed operating-system disk cache.','Baseline timing is in-process and must not be compared as a speedup against process-level search.']})
  if not exact or result['recall_at_5']<1 or result['mrr_at_5']<1: raise SystemExit('benchmark quality gate failed')
  out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print('BENCHMARK_OK'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
