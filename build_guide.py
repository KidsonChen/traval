import re, json, os, urllib.request, time, sys

SRC = 'map.html'
OUT = 'guide.html'
IMG_DIR = 'guide_images'
os.makedirs(IMG_DIR, exist_ok=True)

html = open(SRC, encoding='utf-8').read()

# 用 Node 原生解析 JS 字面量，匯出 JSON（最穩）
node_extract = r'''
const fs=require('fs');
const html=fs.readFileSync('map.html','utf8');
const pm=html.match(/\/\* ===PLACES_START=== \*\/([\s\S]*?)\/\* ===PLACES_END=== \*\//);
const im=html.match(/const IMG = (\{[\s\S]*?\n\});/);
const PLACES = eval('('+pm[1].replace('const PLACES =','').trim().replace(/;$/,'')+')');
const IMG = eval('('+im[1]+')');
fs.writeFileSync('places.json', JSON.stringify(PLACES));
fs.writeFileSync('img.json', JSON.stringify(IMG));
console.log('extracted', PLACES.length, 'places,', Object.keys(IMG).length, 'imgs');
'''
open('_extract.js','w',encoding='utf-8').write(node_extract)
import subprocess
subprocess.run(['node','_extract.js'], check=True)
PLACES = json.load(open('places.json',encoding='utf-8'))
IMG = json.load(open('img.json',encoding='utf-8'))
open('places.json','w',encoding='utf-8').close()
open('img.json','w',encoding='utf-8').close()

# 每日車程/主題（假設 10/19 出發）
DRIVE = {
 1:  ("10/19", "布拉格老城漫步", "市區步行，無自駕車程"),
 2:  ("10/20", "城南＋河景", "市區移動，傍晚伏爾塔瓦河遊船"),
 3:  ("10/21", "東進庫特納霍拉 → CK 山城", "布拉格→庫特納霍拉 83km/1.2h → CK 174km/2.5h（當日約 257km/3.7h）"),
 4:  ("10/22", "跨國 → 哈修塔特 → 薩爾斯堡", "CK→哈修塔特→薩爾斯堡 275km/4.4h"),
 5:  ("10/23", "德國國王湖天氣巡禮", "薩爾斯堡⇄國王湖 90km/1.6h（當日往返，含鷹巢）"),
 6:  ("10/24", "回程捷克 → 皮爾森啤酒之鄉", "薩爾斯堡→皮爾森 290km/4.1h"),
 7:  ("10/25", "卡爾什特因城堡 → 還車返台", "皮爾森→卡爾什特因→機場 103km/1.5h"),
}

def safe(s): return re.sub(r'[\\/:*?"<>|]', '_', s)

# 下載圖片到本地（含重試，避開 429）
def dl(url, path):
    if not url: return False
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (travel-guide)'})
            data = urllib.request.urlopen(req, timeout=12).read()
            open(path,'wb').write(data)
            return True
        except Exception as e:
            wait = 1.5 + attempt*2
            print(f"  重試 {safe(url)[:24]} ({e}) wait {wait}s")
            time.sleep(wait)
    return False

# 建立 名稱->本地路徑 對照（按 PLACES 順序）
name2local = {}
# 不本地下載（Wikimedia 會限流）；改用縮圖參數遠端網址，瀏覽器按需載入即可
def thumb(url):
    # 用 Special:FilePath?width=800 縮圖（穩定 200，不會 400）
    if not url: return ''
    # IMG 網址的檔名已是 URL-encoded，直接取用即可（不要再 quote 一次）
    m = re.search(r'/([^/?#]+\.(?:jpg|jpeg|png|svg|JPG|JPEG|PNG|SVG))$', url)
    if m:
        fname = m.group(1)
        return 'https://commons.wikimedia.org/wiki/Special:FilePath/'+fname+'?width=800'
    return url

name2local = {}
for i,p in enumerate(PLACES):
    nm = p['name']
    remote = IMG.get(nm,'')
    name2local[nm] = thumb(remote)

print("圖片採遠端縮圖網址（不本地下載，開頁時聯網載入）:", sum(1 for v in name2local.values() if v))
IMG_LOCAL = dict(name2local)

# ---- 產生 guide.html ----
CSS = """
:root{--blue:#0B4F8C;--blue2:#1a6fc4;--ink:#222;--muted:#777;--line:#e3e8ef;--bg:#f5f7fa}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"PingFang TC","Microsoft JhengHei",sans-serif;color:var(--ink);background:var(--bg);line-height:1.7}
a{color:var(--blue2);text-decoration:none}
.hero{background:linear-gradient(135deg,#0B4F8C,#1a6fc4 60%,#3a8fd0);color:#fff;padding:46px 20px 38px;text-align:center}
.hero h1{margin:0 0 8px;font-size:30px;letter-spacing:1px}
.hero p{margin:4px 0;opacity:.95}
.chips{margin-top:14px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap}
.chip{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.35);padding:4px 12px;border-radius:20px;font-size:13px}
.toc{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);z-index:5;display:flex;gap:6px;padding:10px;overflow-x:auto;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.toc a{flex:0 0 auto;padding:5px 12px;border-radius:18px;background:#eef6ff;color:var(--blue);font-size:13px;font-weight:600}
.day{max-width:860px;margin:26px auto;background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.04)}
.day-head{background:linear-gradient(135deg,var(--blue),var(--blue2));color:#fff;padding:16px 22px}
.day-head .dnum{font-size:13px;opacity:.9;letter-spacing:2px}
.day-head h2{margin:2px 0 4px;font-size:22px}
.day-head .meta{font-size:12.5px;opacity:.95}
.day-head .drive{margin-top:6px;font-size:12.5px;background:rgba(255,255,255,.15);padding:5px 10px;border-radius:8px;display:inline-block}
.spot{display:flex;gap:14px;padding:16px 22px;border-top:1px solid var(--line)}
.spot:nth-child(odd){background:#fafcff}
.spot img{width:160px;height:120px;object-fit:cover;border-radius:10px;flex:0 0 160px;background:#eee}
.spot .body{flex:1}
.spot h3{margin:0 0 2px;font-size:16px;color:var(--blue)}
.tag{display:inline-block;font-size:11px;color:var(--muted);background:#eef2f7;border-radius:6px;padding:1px 8px;margin-bottom:6px}
.spot p{margin:4px 0 0;font-size:13.5px;color:#333}
.foot{max-width:860px;margin:30px auto;padding:20px;background:#fff;border:1px solid var(--line);border-radius:14px}
.foot h2{color:var(--blue);font-size:18px;margin-top:0}
.foot ul{margin:6px 0;padding-left:20px;font-size:13.5px}
.foot li{margin:4px 0}
.note{font-size:12px;color:var(--muted);text-align:center;margin:18px}
@media(max-width:640px){.spot{flex-direction:column}.spot img{width:100%;height:180px;flex:none}.hero h1{font-size:24px}}
"""

def esc(s): return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

days = sorted({p['day'] for p in PLACES}, key=lambda x:(x if isinstance(x,int) else 999))
toc = ''.join(f'<a href="#day{d}">Day {d}</a>' for d in days if isinstance(d,int))

spots_html = ''
for d in days:
    if not isinstance(d,int): continue
    date, theme, drive = DRIVE.get(d, ("","",""))
    items = [p for p in PLACES if p['day']==d]
    cards = ''
    for p in items:
        local = IMG_LOCAL.get(p['name'],'')
        remote = IMG.get(p['name'],'')
        img_tag = ''
        if local:
            fb = f"this.onerror=null;this.src='{remote}'" if remote else ''
            img_tag = f'<img src="{esc(local)}" alt="{esc(p["name"])}" loading="lazy" onerror="{fb}">'
        elif remote:
            img_tag = f'<img src="{esc(remote)}" alt="{esc(p["name"])}" loading="lazy">'
        note = f'<span class="tag">{esc(p.get("note",""))}</span>' if p.get('note') else ''
        desc = f'<p>{esc(p.get("desc",""))}</p>' if p.get('desc') else ''
        cards += f'<div class="spot">{img_tag}<div class="body"><h3>{esc(p["name"])}</h3>{note}{desc}</div></div>'
    spots_html += f'''
<div class="day" id="day{d}">
  ={d}=
</div>
'''  # placeholder replaced below
    spots_html = spots_html.replace(f'={d}=', f'''<div class="day-head">
    <div class="dnum">DAY {d} ｜ {esc(date)}</div>
    <h2>{esc(theme)}</h2>
    <div class="meta">{len(items)} 個景點 / 住宿</div>
    <div class="drive">🚗 今日車程：{esc(drive)}</div>
  </div>
  {cards}''')

guide = f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>奧捷＋德國國王湖 · 7天自駕攻略</title>
<style>{CSS}</style>
</head>
<body>
<header class="hero">
  <h1>🇨🇿🇦🇹 奧捷＋德國國王湖 · 7天自駕攻略</h1>
  <p>4 人同行 ｜ 10 月賞楓自駕 ｜ 布拉格 → CK → 哈修塔特 → 薩爾斯堡 → 國王湖 → 皮爾森</p>
  <div class="chips">
    <span class="chip">🚗 全程自駕</span>
    <span class="chip">📅 7 天 6 夜</span>
    <span class="chip">🍁 10月賞楓</span>
    <span class="chip">👥 4 人</span>
  </div>
</header>
<nav class="toc">{toc}</nav>
{spots_html}
<section class="foot">
  <h2>📌 實用資訊</h2>
  <ul>
    <li><b>自駕租車：</b>4人含跨國（Cross-Border 允許奧/德），全包約 NT$7,000/人（租車＋全險＋油資＋過路費）。</li>
    <li><b>奧地利 Vignette 貼紙：</b>10日 €11.4（網購或加油站），貼擋風玻璃；德國免費。</li>
    <li><b>停車：</b>哈修塔特付費場(P1/P2)+接駁；國王湖大停車場；奧伊根多夫/安德區住宿附停車。</li>
    <li><b>住宿評價：</b>四間皆優（布拉格9.7 / CK 8.8 / 薩爾斯堡9.5 / 皮爾森9.1），無明顯負評。</li>
    <li><b>必帶：</b>台灣駕照正本＋國際駕照(IDP)＋護照＋本人信用卡。</li>
  </ul>
  <p class="note">日期以 10/19 出發推算（D1=10/19…D7=10/25）。地圖與可編輯版本請見 <a href="map.html">map.html</a>。</p>
</section>
<p class="note">本攻略由 map.html 資料自動產生 ｜ 圖片來源：Wikimedia Commons（免費授權）</p>
</body>
</html>'''

open(OUT,'w',encoding='utf-8').write(guide)
print("已產生", OUT, "大小", os.path.getsize(OUT), "bytes")
