import subprocess,sys
if len(sys.argv)!=2 or sys.argv[1]!='integration': raise SystemExit('usage: check.py integration')
r=subprocess.run([sys.executable,'-m','unittest','-v','tests.test_integration'],text=True)
if r.returncode: raise SystemExit(r.returncode)
print('CHECK_OK')
