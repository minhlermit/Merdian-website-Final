"""Kiểm thử toàn luồng bằng dữ liệu giả lập (không cần mạng): python3 tests/test_pipeline.py"""
import sys, time, json, os, io, contextlib
import tempfile, pathlib
TMP=tempfile.mkdtemp(prefix="sts_test_")
os.environ["STS_CACHE_DIR"]=TMP
ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/".claude/skills/stock-token-scout/scripts"))
import common as c
NVDA="0xd0601ce157db5bdc3162bbac2a2c8af5320d9eec"; TSLA="0x322f0929c4625ed5bad873c95208d54e1c003b2d"
AI="0xaaaa000000000000000000000000000000001e18"; FAKE="0xfa4e000000000000000000000000000000000001"
FAKENVDA="0x9999999999999999999999999999999999999999"; DEP="0xdddd000000000000000000000000000000000001"
USDG="0x5fc5360d0400a0fd4f2af552add042d716f1d168"
now=time.time(); ST={"run":1}
def liq(): return 720000 if ST["run"]==1 else 300000
def dexpair(pool, stock_addr, stock_sym, L, age_days=20):
    R,S=0.0004,180.0
    return {"pairAddress":pool,"dexId":"uniswap","url":"https://dexscreener.com/robinhood/"+pool,
      "baseToken":{"address":AI,"symbol":"AI","name":"Artificial Inu"},"quoteToken":{"address":stock_addr,"symbol":stock_sym},
      "priceNative":str(R),"priceUsd":str(R*S),"liquidity":{"usd":L,"base":5e8,"quote":2000},
      "volume":{"h24":3.1e6,"h6":7e5,"h1":1.2e5},"txns":{"h24":{"buys":5200,"sells":4100}},"priceChange":{"h24":3},
      "fdv":4e7,"marketCap":4e7,"pairCreatedAt":(now-age_days*86400)*1000,
      "info":{"websites":[{"url":"https://ai.example"}],"socials":[{"type":"twitter","url":"https://x.com/ainu"}],"description":"Meme paired with NVDA stock token"}}
def gtpool(addr,base,quote,name,L,chg):
    return {"attributes":{"address":addr,"name":name,"reserve_in_usd":str(L),"volume_usd":{"h24":"900000","h1":"40000"},
      "transactions":{"h24":{"buys":3000,"sells":2500,"buyers":820,"sellers":610}},"price_change_percentage":{"h24":str(chg)},
      "fdv_usd":"9000000","pool_created_at":"2026-09-10T00:00:00Z"},
      "relationships":{"base_token":{"data":{"id":"robinhood_"+base}},"quote_token":{"data":{"id":"robinhood_"+quote}}}}
def ai_pairs():
    ps=[dexpair("0xpool1","0xD0601CE157Db5bdC3162BbaC2a2C8aF5320D9EEC","NVDA",liq())]
    if ST["run"]==2: ps.append(dexpair("0xpool2","0x322F0929c4625eD5bAd873c95208D54E1c003b2d","TSLA",40000, age_days=0.1))
    ps.append(dexpair("0xpool3",FAKENVDA,"NVDA",25000))
    return ps
def fake(url, params=None, retries=3):
    u=url.lower()
    if "trending_pools" in u or "new_pools" in u:
        return {"data":[gtpool("0xpool1",AI,NVDA,"AI / NVDA",liq(),3), gtpool("0xpoolf",FAKE,FAKENVDA,"SCAM / NVDA",60000,500)]}
    if "token-pairs/v1" in u and NVDA in u: return [p for p in ai_pairs() if p["quoteToken"]["address"].lower()==NVDA] + [
        {"pairAddress":"0xnvdausdg","baseToken":{"address":NVDA,"symbol":"NVDA"},"quoteToken":{"address":USDG,"symbol":"USDG"},
         "priceUsd":"181.8","priceNative":"181.8","liquidity":{"usd":2e6}}]
    if "token-pairs/v1" in u and TSLA in u: return [p for p in ai_pairs() if p["quoteToken"]["address"].lower()==TSLA]
    if "token-pairs/v1" in u and AI in u: return ai_pairs()
    if "token-pairs/v1" in u: return []
    if "tokens/v1" in u: return []
    if "/tokens/"+AI+"/pools" in u: return {"data":[gtpool("0xpool1",AI,NVDA,"AI / NVDA",liq(),3)]}
    if "/tokens/"+AI+"/info" in u: return {"data":{"attributes":{"name":"Artificial Inu","symbol":"AI","websites":["https://ai.example"],"twitter_handle":"ainu"}}}
    if "ohlcv" in u:
        cur=params["currency"]; rows=[]
        for i in range(168):
            R=0.0003*(1+0.002*i); S=175*(1+0.0002*i)
            rows.append([int(now)-3600*(168-i),0,0,0,(R if cur=="token" else R*S),1000])
        return {"data":{"attributes":{"ohlcv_list":rows}}}
    if u.endswith("/tokens/"+NVDA): return {"total_supply":str(int(9e5*1e18)),"decimals":"18"}
    if u.endswith("/tokens/"+AI): return {"total_supply":str(int(1e9*1e18)),"decimals":"18","holders_count":"14020" if ST["run"]==1 else "15100"}
    if "/tokens/"+AI+"/holders" in u:
        items=[{"address":{"hash":"0x000000000000000000000000000000000000dead"},"value":str(int(1e8*1e18))},
               {"address":{"hash":"0xlock","is_contract":True,"name":"PonsLiquidityLocker"},"value":str(int(2e8*1e18))}]
        items+=[{"address":{"hash":f"0xe{i:039d}"},"value":str(int((3e7-i*1e6)*1e18))} for i in range(15)]
        items.append({"address":{"hash":DEP},"value":str(int(6e7*1e18))})
        return {"items":items}
    if "/tokens/"+AI+"/transfers" in u:
        return {"items":[{"from":{"hash":f"0xu{i:039d}"},"to":{"hash":"0x000000000000000000000000000000000000dead"},"total":{"value":str(int(1e5*1e18))},"timestamp":"2026-09-22T10:00:00Z"} for i in range(23)]}
    if "/tokens/"+NVDA+"/transfers" in u:
        return {"items":[{"from":{"hash":c.BURN_ZERO},"to":{"hash":"0xissuer"},"total":{"value":"1"},"timestamp":"2026-09-22T10:00:00Z"}]*4}
    if u.endswith("/addresses/"+AI): return {"creator_address_hash":DEP,"is_verified":True,"proxy_type":None}
    if u.endswith("/addresses/"+DEP): return {"is_contract":False}
    if "/smart-contracts/"+AI in u: return {"abi":[{"type":"function","name":n} for n in ["transfer","owner","renounceOwnership","burnForCredits","setFee"]]}
    if "/addresses/"+DEP+"/token-transfers" in u: return {"items":[{"total":{"value":str(int(5e7*1e18))},"to":{"hash":"0xr1"}}]}
    print("UNMOCKED",url); return None
c.get_json=fake
import scout_cycle, onchain, ledger, context, store
import discover
def run_cycle():
    discover.FAKE_PAIRS.clear()
    buf=io.StringIO()
    with contextlib.redirect_stdout(buf): code=scout_cycle.run(5)
    return code
assert run_cycle()==10
con=store.connect(); con.execute("UPDATE snapshots SET ts=ts-6*3600"); con.execute("UPDATE events SET ts=ts-13*3600"); con.commit()
ST["run"]=2
assert run_cycle()==10
q={x["symbol"]:x["events"] for x in c.load_cache("queue.json")["queue"]}
assert q["SCAM"]==["FAKE_STOCK_PAIR"], q
assert {"LIQUIDITY_COLLAPSE","NEW_STOCK_PAIRED_POOL","NEW_CANDIDATE"} <= set(q["AI"]), q
con=store.connect()
det=json.loads(con.execute("SELECT detail FROM events WHERE type='LIQUIDITY_COLLAPSE'").fetchone()["detail"])
assert det["cause_hints"] and all(h["level"] in ("LIKELY","UNCONFIRMED") for h in det["cause_hints"])
r=onchain.build(AI); onchain.md(r)
assert r["suspected_fake_stock_pairs"] and r["suspected_fake_stock_pairs"][0]["counter_addr"]==FAKENVDA
assert "R_chg_window" in r["history_7d"] and r["stock_pair"]["canonical"] is True
assert r["supply_flows"]["unique_burners"]==23
# ledger: page (mock urlopen)
class R:
    def __init__(s,b): s.b=b
    def read(s,n=-1): return s.b
    def __enter__(s): return s
    def __exit__(s,*a): pass
PAGE=[b"<html>Artificial Inu. Burn $AI to get AI credits. Built by @alicebuilds. CA: "+AI.encode()+b" <a href='https://x.com/ainu'>X</a></html>"]
ledger.urllib.request.urlopen=lambda req,timeout=20: R(PAGE[0])
def L(*args):
    sys.argv=["ledger.py",*args]; buf=io.StringIO()
    with contextlib.redirect_stdout(buf): ledger.main()
    return buf.getvalue()
assert json.loads(L("page","--token",AI,"--url","https://ai.example","--official"))["status"]=="NEW"
assert json.loads(L("page","--token",AI,"--url","https://ai.example","--official"))["status"]=="UNCHANGED"
PAGE[0]=PAGE[0].replace(b"credits.",b"credits. Now live on mainnet.")
out=json.loads(L("page","--token",AI,"--url","https://ai.example","--official")); assert out["status"]=="CHANGED" and out["diff"]==["+Now live on mainnet."], out
json.dump([{"url":"https://x.com/ainu/status/1","source":"x","category":"identity","author":"@ainu","text":"Built by @alicebuilds"},
           {"url":"https://x.com/ainu/status/2","source":"x","category":"event","author":"@ainu","text":"AI credits burn live"}],open(TMP+"/items.json","w"))
assert json.loads(L("evidence","add-batch","--token",AI,"--file",TMP+"/items.json"))["new"]==2
assert json.loads(L("evidence","add-batch","--token",AI,"--file",TMP+"/items.json"))["new"]==0
L("bridge","add","--token",AI,"--subject","project","--entity","@ainu","--type","x_links_contract","--url","https://x.com/ainu/status/3")
L("bridge","add","--token",AI,"--subject","creator","--entity","@alicebuilds","--type","project_names_creator","--url","https://x.com/ainu/status/1")
lv={(a["subject"],a["entity"]):a["level"] for a in json.loads(L("bridge","show","--token",AI))}
assert lv[("creator","@alicebuilds")]=="LIKELY" and lv[("project","@ainu")]=="VERIFIED_OFFCHAIN", lv
L("bridge","add","--token",AI,"--subject","creator","--entity","@alicebuilds","--type","creator_self_claim_with_contract","--url","https://x.com/alicebuilds/status/9")
lv={(a["subject"],a["entity"]):a["level"] for a in json.loads(L("bridge","show","--token",AI))}
assert lv[("creator","@alicebuilds")]=="VERIFIED_OFFCHAIN", lv
blocked=False
try: L("bridge","add","--token",AI,"--subject","wallet","--entity",DEP,"--type","wallet_relationship","--url","x")
except SystemExit: blocked=True
assert blocked
for t,a in [("paired_with","NVDA"),("paired_with","TSLA"),("burn_mechanism",""),("stock_backed",""),("team_allocation","5"),("contract_address",AI),("fixed_supply","")]:
    L("claim","add","--token",AI,"--type",t,"--arg",a,"--claim",f"claim {t} {a}","--url","https://ai.example")
st={(x["ctype"],x["arg"]):x["status"] for x in json.loads(L("claim","verify","--token",AI))}
exp={("paired_with","NVDA"):"VERIFIED_ONCHAIN",("paired_with","TSLA"):"VERIFIED_ONCHAIN",("burn_mechanism",""):"VERIFIED_ONCHAIN",
     ("stock_backed",""):"CONFLICT",("team_allocation","5"):"CONFLICT",("contract_address",AI):"VERIFIED_ONCHAIN",("fixed_supply",""):"VERIFIED_ONCHAIN"}
assert st==exp, st
b=context.build(AI)
assert len(b["new_evidence"])==2 and len(json.dumps(b,ensure_ascii=False))<20000
sys.argv=["context.py",AI,"--mark-handled","--summary","test"]
with contextlib.redirect_stdout(io.StringIO()): context.main()
b=context.build(AI); assert b["new_evidence"]==[] and b["open_events"]==[] and b["previous_report_summary"]["text"]=="test"
print("ALL TESTS PASSED")
