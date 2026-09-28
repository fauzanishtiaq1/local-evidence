"""Offline deterministic BM25 index with citation-preserving snapshots."""
from __future__ import annotations
import hashlib, json, math, os, re, shutil, tempfile
from pathlib import Path, PurePosixPath
from collections import Counter, defaultdict

SCHEMA_VERSION = 1
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)

class IndexErrorBase(Exception): pass
class InvalidIndexError(IndexErrorBase): pass
class SourceChangedError(IndexErrorBase): pass

def _tokens(s): return [m.group(0).casefold() for m in _TOKEN.finditer(s)]
def _sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def _safe(root, p):
    root = Path(root).resolve(); q = Path(p)
    try: r = q.resolve(strict=False); r.relative_to(root)
    except ValueError: raise ValueError("path escapes source directory")
    return r
def _validate_dirs(source, index):
    s = Path(source).resolve(); i = Path(index).resolve()
    if i == s or i in s.parents: raise ValueError("index directory cannot be source or its ancestor")
    return s, i
def _write_json(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")

def build_index(source_dir, index_dir, *, extensions=(".md", ".txt", ".rst"), chunk_lines=40, overlap_lines=5):
    if isinstance(chunk_lines,bool) or isinstance(overlap_lines,bool) or not isinstance(chunk_lines,int) or not isinstance(overlap_lines,int) or chunk_lines <= 0 or overlap_lines < 0 or overlap_lines >= chunk_lines: raise ValueError("invalid chunk parameters")
    source, dest = _validate_dirs(source_dir, index_dir)
    if not source.is_dir(): raise ValueError("source directory does not exist")
    ext = {e if e.startswith(".") else "." + e for e in extensions}
    files=[]
    for p in source.rglob("*"):
        try:
            resolved = p.resolve(strict=False)
            if resolved == dest or dest in resolved.parents: continue
        except OSError: continue
        if p.is_symlink():
            if p.is_dir() or not _safe(source,p).is_relative_to(source): continue
        if p.is_file() and p.suffix in ext:
            q = _safe(source,p); files.append((q.relative_to(source).as_posix(),q))
    files.sort(); chunks=[]; docs=[]; postings=defaultdict(list)
    step=chunk_lines-overlap_lines
    for rel,p in files:
        try: text=p.read_text(encoding="utf-8")
        except UnicodeDecodeError as e: raise ValueError(f"undecodable UTF-8 file: {rel}") from e
        lines=text.splitlines(); digest=_sha(text); docs.append({"path":rel,"sha256":digest,"text":text})
        for start in range(0,len(lines),step):
            end=min(len(lines),start+chunk_lines); body="\n".join(lines[start:end])
            if not body: continue
            cid=f"{rel}:{start+1}-{end}"; toks=_tokens(body); chunks.append({"id":cid,"path":rel,"start_line":start+1,"end_line":end,"text":body,"length":len(toks)})
            for term,n in Counter(toks).items(): postings[term].append([cid,n])
            if end>=len(lines): break
    n=len(chunks); df={t:len(v) for t,v in postings.items()}; avg=sum(c["length"] for c in chunks)/n if n else 0
    meta={"schema_version":1,"tokenizer":"unicode-casefold-letters-digits","bm25":{"k1":1.2,"b":0.75},"parameters":{"chunk_lines":chunk_lines,"overlap_lines":overlap_lines,"extensions":sorted(ext)},"source_dir":str(source),"files":len(docs),"chunks":n,"vocabulary":len(df)}
    payload={"metadata":meta,"documents":docs,"chunks":chunks,"postings":dict(sorted(postings.items())),"df":df,"avgdl":avg}
    parent=dest.parent; parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and (not dest.is_dir() or dest.is_symlink() or not (dest/"index.json").is_file()): raise ValueError("refusing to replace arbitrary directory")
    dest.mkdir(exist_ok=True)
    tmp=Path(tempfile.mkdtemp(prefix=dest.name+".tmp-",dir=str(parent)))
    try:
        _write_json(tmp/"index.json",payload); _load(tmp)
        os.replace(tmp/"index.json",dest/"index.json"); tmp.rmdir()
    except Exception:
        shutil.rmtree(tmp,ignore_errors=True); raise
    return {"files":len(docs),"chunks":n,"vocabulary":len(df),"index_dir":str(dest)}

def _load(index_dir):
    p=Path(index_dir).resolve(); f=p/"index.json"
    if not f.is_file(): raise InvalidIndexError("missing index.json")
    try: x=json.loads(f.read_text(encoding="utf-8"))
    except Exception as e: raise InvalidIndexError("malformed index") from e
    try:
        m=x["metadata"]
        if m["schema_version"] != 1: raise ValueError()
        if not (isinstance(m["bm25"]["k1"],(int,float)) and math.isfinite(m["bm25"]["k1"]) and m["bm25"]["k1"]>0 and isinstance(m["bm25"]["b"],(int,float)) and 0<=m["bm25"]["b"]<=1 and math.isfinite(x["avgdl"])): raise ValueError()
        cs=x["chunks"]; ids=[c["id"] for c in cs];
        if len(ids)!=len(set(ids)): raise ValueError()
        cmap={c["id"]:c for c in cs}
        for c in cs:
            if not (c["start_line"]>=1 and c["end_line"]>=c["start_line"] and isinstance(c["text"],str)): raise ValueError()
        for t,arr in x["postings"].items():
            seen=set()
            for cid,n in arr:
                if not (cid in cmap and isinstance(n,int) and n>0): raise ValueError()
            for cid,n in arr:
                if cid in seen: raise ValueError()
                seen.add(cid)
        if set(x["df"]) != set(x["postings"]): raise ValueError()
        for t,arr in x["postings"].items():
            if x["df"][t] != len(arr): raise ValueError()
        documents = {}
        for d in x["documents"]:
            rel = d["path"]
            q = PurePosixPath(rel)
            if not isinstance(rel, str) or not rel or q.is_absolute() or '..' in q.parts or '\\' in rel or ':' in rel or rel in documents or str(q) != rel:
                raise ValueError()
            if not re.fullmatch(r"[0-9a-f]{64}",d["sha256"]): raise ValueError()
            if not isinstance(d.get("text"),str) or _sha(d["text"]) != d["sha256"]: raise ValueError()
            documents[rel] = d
        expected_postings = defaultdict(list)
        for c in cs:
            if c['path'] not in documents:
                raise ValueError()
            start, end = c['start_line'], c['end_line']
            lines = documents[c['path']]['text'].splitlines()
            if type(start) is not int or type(end) is not int or end > len(lines):
                raise ValueError()
            if c['text'] != '\n'.join(lines[start-1:end]) or c['id'] != f"{c['path']}:{start}-{end}":
                raise ValueError()
            tokens = _tokens(c['text'])
            if type(c['length']) is not int or c['length'] != len(tokens):
                raise ValueError()
            for term, frequency in Counter(tokens).items():
                expected_postings[term].append([c['id'],frequency])
        if dict(expected_postings) != x['postings']:
            raise ValueError()
        expected_average = sum(c['length'] for c in cs) / len(cs) if cs else 0
        if x['avgdl'] != expected_average or m['files'] != len(documents) or m['chunks'] != len(cs) or m['vocabulary'] != len(x['postings']):
            raise ValueError()
        if m['bm25'] != {'k1':1.2,'b':0.75} or m['tokenizer'] != 'unicode-casefold-letters-digits':
            raise ValueError()
        params = m['parameters']
        if type(params['chunk_lines']) is not int or type(params['overlap_lines']) is not int or not 0 <= params['overlap_lines'] < params['chunk_lines']:
            raise ValueError()
    except Exception as e: raise InvalidIndexError("invalid index structure") from e
    return x

def search_index(index_dir, query, *, top_k=5, min_score=0.0):
    if not isinstance(query,str) or not query.strip() or isinstance(top_k,bool) or not isinstance(top_k,int) or top_k<1 or not isinstance(min_score,(int,float)) or not math.isfinite(min_score): raise ValueError("invalid query parameters")
    x=_load(index_dir); terms=set(_tokens(query)); chunks={c["id"]:c for c in x["chunks"]}; N=len(chunks); avg=x["avgdl"] or 1; out=[]
    documents = {d['path']:d for d in x['documents']}
    scores=defaultdict(float)
    for t in sorted(terms):
        arr=x["postings"].get(t,[]); df=len(arr)
        idf=math.log(1+(N-df+0.5)/(df+0.5))
        for cid,tf in arr:
            c=chunks[cid]; scores[cid] += idf * (tf*2.2/(tf+1.2*(1-0.75+0.75*c["length"]/avg)))
    for cid,score in scores.items():
        c=chunks[cid]
        if score>=min_score and score>0: out.append({"rank":0,"score":score,"path":c["path"],"start_line":c["start_line"],"end_line":c["end_line"],"text":c["text"],"source_sha256":documents[c['path']]['sha256'],"chunk_id":cid})
    out.sort(key=lambda h:(-h["score"],h["path"],h["start_line"],h["chunk_id"]))
    for i,h in enumerate(out[:top_k],1): h["rank"]=i
    return out[:top_k]

def inspect_document(index_dir, path, *, start_line, end_line):
    x=_load(index_dir); rel=Path(path).as_posix(); d=next((d for d in x["documents"] if d["path"]==rel),None)
    if not d: raise FileNotFoundError(path)
    root=Path(x["metadata"]["source_dir"]).resolve(); p=(root/Path(rel)).resolve()
    if Path(rel).is_absolute() or root not in p.parents or p.is_symlink(): raise InvalidIndexError("unsafe indexed path")
    try: text=p.read_text(encoding="utf-8")
    except Exception as e: raise SourceChangedError(rel) from e
    if _sha(text)!=d["sha256"]: raise SourceChangedError(rel)
    lines=text.splitlines();
    if start_line<1 or end_line<start_line or start_line>len(lines): raise ValueError("invalid line range")
    return {"path":rel,"start_line":start_line,"end_line":min(end_line,len(lines)),"text":"\n".join(lines[start_line-1:end_line]),"source_sha256":d["sha256"]}

def index_stats(index_dir):
    x=_load(index_dir); m=x["metadata"]; return {"schema_version":1,"files":m["files"],"chunks":m["chunks"],"vocabulary":m["vocabulary"],"bytes":(Path(index_dir)/"index.json").stat().st_size,"parameters":m["parameters"]}
