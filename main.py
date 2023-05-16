import json

fCfg = open("cfg.json","r")
Cfg = json.loads(fCfg.read())
fCfg.close()

print(Cfg.keys())