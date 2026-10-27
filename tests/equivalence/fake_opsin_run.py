"""names_to_smiles of one version with the OPSIN web service replaced by a fixed lookup table
(the SMILES OPSIN gave in the original run), so both versions get the same answers offline.
usage: python fake_opsin_run.py TOOL_ROOT compounds.xlsx out.xlsx reference_smiles.xlsx"""
import importlib.util, io, json, os, sys
from urllib.error import HTTPError

root, inp, out, ref = sys.argv[1:5]
sys.path.insert(0, os.path.join(root, "names_to_smiles"))
spec = importlib.util.spec_from_file_location("names_to_smiles", os.path.join(root, "names_to_smiles", "names_to_smiles.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

import openpyxl
from urllib.parse import unquote
ws = openpyxl.load_workbook(ref, read_only=True).active
data = list(ws.iter_rows(values_only=True))
head = [str(x).lower() for x in data[0]]
N, SM, ST = head.index("name"), head.index("smiles"), head.index("opsin_status")
ok = {}
for r in data[1:]:
    if r[N] and r[SM] and str(r[ST]).startswith("OK"):
        ok[str(r[N]).strip()] = r[SM]
        if "repaired" in str(r[ST]):
            ok["__repaired__" + str(r[N]).strip()] = r[SM]


class Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def fake_urlopen(req, timeout=None):
    url = req.full_url if hasattr(req, "full_url") else req
    name = unquote(url.rsplit("/", 1)[1][:-5])
    if name in ok and "__repaired__" + name not in ok:
        return Resp(json.dumps({"status": "SUCCESS", "smiles": ok[name]}).encode())
    # a repaired variant succeeds if the original name was repaired in the reference run
    for k, v in ok.items():
        if k.startswith("__repaired__") and name != k[12:] and name.replace(" ", "") == k[12:].replace(" ", "").replace("-", "", 0):
            return Resp(json.dumps({"status": "SUCCESS", "smiles": v}).encode())
    if "zzfail500" in name:
        raise HTTPError(url, 500, "err", {}, io.BytesIO(b"not json"))
    raise HTTPError(url, 404, "nf", {}, io.BytesIO(json.dumps({"status": "FAILURE", "message": "name not parsed: " + name[:40]}).encode()))


m.urlopen = fake_urlopen
m.time.sleep = lambda s: None
m.main(inp, out)
