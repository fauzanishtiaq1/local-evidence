import hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
PYTHON = sys.executable

class CliIntegrationTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([PYTHON, "-m", "local_evidence", *map(str, args)], cwd=ROOT, text=True, capture_output=True)

    def test_build_search_inspect_and_exact_snapshot_citation(self):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td); src=t/'src'; idx=t/'idx'; src.mkdir()
            p=src/'notes.md'; original='\ncache invalidation requires a version check\n\nretain the source line\n'
            p.write_text(original, encoding='utf-8')
            b=self.run_cli('build',src,idx,'--chunk-lines','1','--overlap-lines','0')
            self.assertEqual(b.returncode,0,b.stderr); self.assertEqual(json.loads(b.stdout)['files'],1)
            s=self.run_cli('search',idx,'cache invalidation'); self.assertEqual(s.returncode,0,s.stderr)
            hit=json.loads(s.stdout)[0]; self.assertEqual(hit['path'],'notes.md'); self.assertEqual(hit['start_line'],2)
            self.assertEqual(hit['source_sha256'],hashlib.sha256(original.encode()).hexdigest())
            self.assertEqual(hit['text'],'cache invalidation requires a version check')
            i=self.run_cli('inspect',idx,'notes.md','--start-line',2,'--end-line',2); self.assertEqual(i.returncode,0,i.stderr)
            self.assertEqual(json.loads(i.stdout)['text'],hit['text'])
            p.write_text(original.replace('version','tampered'),encoding='utf-8')
            stale=self.run_cli('inspect',idx,'notes.md','--start-line',2,'--end-line',2)
            # The public contract requires a clear nonzero stale-snapshot result.
            self.assertEqual(stale.returncode,1); self.assertIn("source changed",stale.stderr)

    def test_negative_inputs_and_tampered_index(self):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td); src=t/'src'; idx=t/'idx'; src.mkdir(); (src/'x.md').write_text('needle',encoding='utf-8')
            self.assertEqual(self.run_cli('build',src,idx).returncode,0)
            for args in [('search',idx,''),('search',idx,'x','--top-k','0')]:
                self.assertEqual(self.run_cli(*args).returncode,2)
            self.assertNotEqual(self.run_cli('inspect',idx,'missing.md','--start-line','1','--end-line','1').returncode,0)
            data=json.loads((idx/'index.json').read_text()); data['chunks'][0]['text']='forged'; (idx/'index.json').write_text(json.dumps(data))
            bad=self.run_cli('search',idx,'needle'); self.assertEqual(bad.returncode,1); self.assertIn('invalid index',bad.stderr.lower())

    def test_nested_index_and_blank_first_line(self):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td); src=t/'src'; idx=src/'index'; src.mkdir(); (src/'doc.md').write_text('\nneedle evidence\n',encoding='utf-8')
            (src/'ignore.md').write_text('nested index must not be indexed',encoding='utf-8')
            self.assertEqual(self.run_cli('build',src,idx,'--chunk-lines','1','--overlap-lines','0').returncode,0)
            self.assertEqual(json.loads(self.run_cli('search',idx,'needle').stdout)[0]['start_line'],2)
            (idx/'nested.md').write_text('private',encoding='utf-8')
            self.assertEqual(json.loads(self.run_cli('stats',idx).stdout)['files'],2)

if __name__ == '__main__': unittest.main()
