import json, unittest, tempfile, subprocess, sys
from unittest.mock import patch
from pathlib import Path
from local_evidence.core import build_index, search_index, inspect_document, index_stats, InvalidIndexError, SourceChangedError
class CoreTests(unittest.TestCase):
 def setUp(self): self.tmp=tempfile.TemporaryDirectory()
 def tearDown(self): self.tmp.cleanup()
 def test_build_search_stats_and_inspect(self):
  t=Path(self.tmp.name); src=t/'src'; idx=t/'idx'; src.mkdir(); (src/'a.md').write_text('Alpha method\nUnicode caf\\u00e9\nBeta result\n',encoding='utf8')
  r=build_index(src,idx,chunk_lines=2,overlap_lines=0); self.assertEqual(r['chunks'],2)
  hits=search_index(idx,'Alpha',top_k=2); self.assertTrue(hits); self.assertEqual(hits[0]['path'],'a.md'); self.assertEqual(index_stats(idx)['schema_version'],1)
 def test_stale_source_and_malformed_index(self):
  t=Path(self.tmp.name); src=t/'src'; idx=t/'idx'; src.mkdir(); p=src/'x.txt'; p.write_text('hello world',encoding='utf8'); build_index(src,idx); p.write_text('changed',encoding='utf8')
  with self.assertRaises(SourceChangedError): inspect_document(idx,'x.txt',start_line=1,end_line=1)
  d=json.loads((idx/'index.json').read_text()); d['metadata']['schema_version']=99; (idx/'index.json').write_text(json.dumps(d))
  with self.assertRaises(InvalidIndexError): index_stats(idx)
 def test_rebuild_failure_keeps_existing(self):
  t=Path(self.tmp.name); src=t/'src'; idx=t/'idx'; src.mkdir(); (src/'x.md').write_text('stable',encoding='utf8'); build_index(src,idx); before=(idx/'index.json').read_bytes(); (src/'bad.md').write_bytes(bytes([255]))
  with self.assertRaises(ValueError): build_index(src,idx)
  self.assertEqual((idx/'index.json').read_bytes(),before)
 def test_bad_geometry(self):
  t=Path(self.tmp.name); src=t/'src'; src.mkdir()
  with self.assertRaises(ValueError): build_index(src,t/'i',chunk_lines=1,overlap_lines=1)
 def test_paths_empty_nested_and_unicode(self):
  t=Path(self.tmp.name); src=t/'src'; src.mkdir(); (src/'empty.md').write_text('',encoding='utf8'); (src/'u.md').write_text('Straße CAFÉ',encoding='utf8')
  with self.assertRaises(ValueError): build_index(src,src/'..')
  nested=src/'idx'; r=build_index(src,nested); self.assertEqual(r['files'],2); self.assertTrue(search_index(nested,'STRASSE'))
  self.assertEqual(index_stats(nested)['files'],2)
 def test_missing_source_and_numeric_query_rejected(self):
  t=Path(self.tmp.name); missing=t/'missing';
  with self.assertRaises(ValueError): build_index(missing,t/'idx')
  self.assertFalse(missing.exists()); src=t/'src'; src.mkdir(); (src/'x.md').write_text('x') ; build_index(src,t/'idx')
  for args in [('',1,0.0),('x',True,0.0),('x',1,float('nan'))]:
   with self.assertRaises(ValueError): search_index(t/'idx',args[0],top_k=args[1],min_score=args[2])
 def test_atomic_replace_failure_and_sentinel(self):
  t=Path(self.tmp.name); src=t/'src'; idx=t/'idx'; src.mkdir(); (src/'x.md').write_text('old'); build_index(src,idx); old=(idx/'index.json').read_bytes(); (idx/'sentinel').write_text('keep'); (src/'x.md').write_text('new')
  import local_evidence.core as core
  with patch.object(core.os,'replace',side_effect=OSError('injected')):
   with self.assertRaises(OSError): build_index(src,idx)
  self.assertEqual((idx/'index.json').read_bytes(),old); self.assertEqual((idx/'sentinel').read_text(),'keep')
 def test_malformed_path_hash_posting_even_optimized(self):
  t=Path(self.tmp.name); src=t/'src'; idx=t/'idx'; src.mkdir(); (src/'x.md').write_text('x'); build_index(src,idx); base=json.loads((idx/'index.json').read_text())
  for mutate in [lambda d:d['documents'][0].update(path='../escape.md'),lambda d:d['documents'][0].update(sha256='0'*64),lambda d:d['postings'].update(x=[['bad',1]])]:
   d=json.loads(json.dumps(base)); mutate(d); (idx/'index.json').write_text(json.dumps(d));
   code="from local_evidence.core import index_stats; index_stats(r'"+str(idx)+"')"
   self.assertNotEqual(subprocess.run([sys.executable,'-O','-c',code],capture_output=True).returncode,0)
  (idx/'index.json').write_text(json.dumps(base))
 def test_inspect_bounds_and_symlink_stale(self):
  t=Path(self.tmp.name); src=t/'src'; idx=t/'idx'; src.mkdir(); p=src/'x.md'; p.write_text('one'); build_index(src,idx)
  with self.assertRaises(ValueError): inspect_document(idx,'x.md',start_line=2,end_line=2)
  try:
   p.unlink(); p.symlink_to(t/'outside.md'); (t/'outside.md').write_text('one')
  except OSError: self.skipTest("symlink creation unavailable")
  with self.assertRaises(Exception): inspect_document(idx,'x.md',start_line=1,end_line=1)

 def test_blank_first_chunk_nested_rebuild_and_tampered_citation(self):
  t=Path(self.tmp.name);src=t/'src';src.mkdir();(src/'x.md').write_text('\nneedle\n',encoding='utf-8');idx=src/'index'
  build_index(src,idx,chunk_lines=1,overlap_lines=0)
  self.assertEqual(search_index(idx,'needle')[0]['start_line'],2)
  (idx/'private.md').write_text('not a source')
  self.assertEqual(build_index(src,idx,chunk_lines=1,overlap_lines=0)['files'],1)
  self.assertEqual(list(src.glob('index.tmp-*')),[])
  data=json.loads((idx/'index.json').read_text());data['chunks'][0]['text']='forged citation'
  (idx/'index.json').write_text(json.dumps(data))
  with self.assertRaises(InvalidIndexError):search_index(idx,'needle')
