"""Interfaccia web per lo scontorno: trascini la foto, riscarichi il PNG.

    python3 server.py            # poi apri http://127.0.0.1:8000
    python3 server.py --porta 9000 --modello isnet

Il modello resta caricato in memoria tra una foto e l'altra: la prima richiesta
paga il caricamento, le altre stanno sotto il secondo. Nessuna foto lascia la
macchina e niente viene scritto su disco dal server.
"""
import argparse, io, os, sys, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # lanciabile da ovunque
import scontorno as S

LIMITE = 30 * 1024 * 1024        # oltre, la foto viene rifiutata
_lock = threading.Lock()         # onnxruntime: una inferenza per volta

PAGINA = """<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Scontorno</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><text y='14' font-size='14'>\u2702</text></svg>">
<style>
 :root{--bg:#131316;--fg:#f2f2ef;--dim:#8c8c93;--acid:#e4ff3c;--line:#2a2a30}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif}
 header{padding:22px 24px 6px;display:flex;align-items:baseline;gap:14px;flex-wrap:wrap}
 h1{font-size:19px;margin:0;letter-spacing:.02em}
 header p{margin:0;color:var(--dim);font-size:13px}
 main{padding:16px 24px 64px;max-width:1100px}
 #drop{border:2px dashed var(--line);border-radius:14px;padding:44px 20px;text-align:center;
   cursor:pointer;transition:.15s;background:#16161a}
 #drop:hover,#drop.on{border-color:var(--acid);background:#1b1b20}
 #drop b{display:block;font-size:17px;margin-bottom:6px}
 #drop span{color:var(--dim);font-size:13px}
 .opz{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin:18px 0 6px;font-size:13px;color:var(--dim)}
 .opz label{display:flex;gap:7px;align-items:center}
 select,input[type=color]{background:#1b1b20;color:var(--fg);border:1px solid var(--line);
   border-radius:7px;padding:5px 8px;font:inherit;font-size:13px}
 input[type=color]{padding:2px;width:38px;height:29px}
 .griglia{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin-top:22px}
 .card{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:#16161a}
 .tela{height:230px;display:flex;align-items:center;justify-content:center;
   background-color:#e9e9ea;
   background-image:linear-gradient(45deg,#c9c9cc 25%,transparent 25%),linear-gradient(-45deg,#c9c9cc 25%,transparent 25%),
     linear-gradient(45deg,transparent 75%,#c9c9cc 75%),linear-gradient(-45deg,transparent 75%,#c9c9cc 75%);
   background-size:18px 18px;background-position:0 0,0 9px,9px -9px,-9px 0}
 .tela img{max-width:100%;max-height:100%;display:block}
 .info{padding:9px 11px;font-size:12px;color:var(--dim);display:flex;justify-content:space-between;gap:8px;align-items:center}
 .info .nome{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
 a.scarica{color:#131316;background:var(--acid);text-decoration:none;border-radius:6px;
   padding:4px 9px;font-weight:600;font-size:12px;white-space:nowrap}
 .lavora{color:var(--acid)}.errore{color:#ff6b6b}
 footer{color:var(--dim);font-size:12px;padding:0 24px 40px;max-width:1100px}
 code{background:#1b1b20;padding:1px 5px;border-radius:4px}
</style></head><body>
<header><h1>Scontorno</h1><p>tutto in locale — le foto non escono da questa macchina</p></header>
<main>
 <div id="drop" tabindex="0"><b>Trascina qui le foto</b><span>oppure clicca per sceglierle, o incolla con Ctrl+V</span></div>
 <input id="file" type="file" accept="image/*" multiple hidden>
 <div class="opz">
  <label>modo <select id="modo">
    <option value="auto">auto</option><option value="rete">rete</option><option value="tinta">fondo unito</option></select></label>
  <label>modello <select id="modello">__MODELLI__</select></label>
  <label>sfondo <select id="sfondo">
    <option value="">trasparente</option><option value="bianco">bianco</option>
    <option value="nero">nero</option><option value="custom">colore…</option></select>
   <input type="color" id="colore" value="#ffffff" hidden></label>
  <label><input type="checkbox" id="ritaglia"> ritaglia al soggetto</label>
 </div>
 <div class="griglia" id="griglia"></div>
</main>
<footer>Da riga di comando: <code>python3 scontorno.py foto.jpg</code> — stessa resa, anche in blocco.</footer>
<script>
const drop=document.getElementById('drop'), file=document.getElementById('file'),
      griglia=document.getElementById('griglia'), sfondo=document.getElementById('sfondo'),
      colore=document.getElementById('colore');
sfondo.onchange=()=>colore.hidden=sfondo.value!=='custom';
drop.onclick=()=>file.click();
drop.onkeydown=e=>{if(e.key==='Enter'||e.key===' ')file.click()};
file.onchange=()=>{manda([...file.files]);file.value=''};
['dragenter','dragover'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.add('on')}));
['dragleave','drop'].forEach(t=>drop.addEventListener(t,e=>{e.preventDefault();drop.classList.remove('on')}));
drop.addEventListener('drop',e=>manda([...e.dataTransfer.files].filter(f=>f.type.startsWith('image/'))));
addEventListener('paste',e=>{const f=[...e.clipboardData.files].filter(f=>f.type.startsWith('image/'));if(f.length)manda(f)});

function manda(files){files.forEach(uno)}
async function uno(f){
 const card=document.createElement('div');card.className='card';
 card.innerHTML='<div class="tela"></div><div class="info"><span class="nome"></span><span class="stato lavora">lavoro…</span></div>';
 card.querySelector('.nome').textContent=f.name;
 griglia.prepend(card);
 const q=new URLSearchParams({modo:document.getElementById('modo').value,
   modello:document.getElementById('modello').value,
   ritaglia:document.getElementById('ritaglia').checked?'1':'',
   sfondo:sfondo.value==='custom'?colore.value.slice(1):sfondo.value});
 const t=performance.now();
 try{
  const r=await fetch('/api/scontorna?'+q,{method:'POST',body:f});
  if(!r.ok) throw new Error(await r.text());
  const blob=await r.blob(), url=URL.createObjectURL(blob);
  const nome=f.name.replace(/\.[^.]+$/,'')+'-scontornata.png';
  card.querySelector('.tela').innerHTML='<img>';
  card.querySelector('img').src=url;
  const info=card.querySelector('.info');
  info.querySelector('.stato').outerHTML=
    '<a class="scarica" download="'+nome+'" href="'+url+'">PNG · '+((performance.now()-t)/1000).toFixed(1)+'s</a>';
 }catch(e){
  const s=card.querySelector('.stato');s.className='stato errore';s.textContent=String(e.message||e).slice(0,120);
 }
}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = 'scontorno'
    modello = S.PREDEFINITO

    def log_message(self, fmt, *a):
        sys.stderr.write('%s %s\n' % (self.address_string(), fmt % a))

    def _testa(self, code, tipo, lung=None, extra=()):
        self.send_response(code)
        self.send_header('Content-Type', tipo)
        if lung is not None:
            self.send_header('Content-Length', str(lung))
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        if urllib.parse.urlparse(self.path).path not in ('/', '/index.html'):
            self._testa(404, 'text/plain; charset=utf-8', 0)
            return
        opzioni = ''.join(
            f'<option value="{n}"{" selected" if n == self.modello else ""}>{n}</option>'
            for n in S.MODELLI)
        corpo = PAGINA.replace('__MODELLI__', opzioni).encode()
        self._testa(200, 'text/html; charset=utf-8', len(corpo))
        self.wfile.write(corpo)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != '/api/scontorna':
            self._testa(404, 'text/plain; charset=utf-8', 0)
            return
        q = urllib.parse.parse_qs(u.query)
        uno = lambda k, d='': q.get(k, [d])[0]
        try:
            n = int(self.headers.get('Content-Length', 0))
            if n <= 0 or n > LIMITE:
                raise ValueError(f'foto assente o oltre {LIMITE // (1<<20)} MB')
            dati = self.rfile.read(n)
            img = Image.open(io.BytesIO(dati))
            img.load()
            sfondo = S._colore(uno('sfondo')) if uno('sfondo') else None
            t = time.time()
            with _lock:
                out, strada = scontorna_sicuro(
                    img,
                    modo=uno('modo', 'auto'),
                    modello=uno('modello', self.modello),
                    sfondo=sfondo,
                    ritaglia=bool(uno('ritaglia')))
            buf = io.BytesIO()
            out.save(buf, 'PNG')
            corpo = buf.getvalue()
            self.log_message('%s %.1fs %d KB', strada, time.time() - t, len(corpo) // 1024)
            self._testa(200, 'image/png', len(corpo), [('X-Strada', strada)])
            self.wfile.write(corpo)
        except Exception as e:
            msg = f'{type(e).__name__}: {e}'.encode()
            self._testa(400, 'text/plain; charset=utf-8', len(msg))
            self.wfile.write(msg)


def scontorna_sicuro(img, **kw):
    if kw.get('modo') not in ('auto', 'rete', 'tinta'):
        raise ValueError('modo non valido')
    if kw.get('modello') not in S.MODELLI:
        raise ValueError('modello non valido')
    return S.scontorna(img, log=lambda *x: None, **kw)


def main(argv=None):
    p = argparse.ArgumentParser(description='Interfaccia web per lo scontorno.')
    p.add_argument('--porta', type=int, default=8000)
    p.add_argument('--host', default='127.0.0.1', help='0.0.0.0 per esporlo in rete locale')
    p.add_argument('--modello', choices=tuple(S.MODELLI), default=S.PREDEFINITO)
    a = p.parse_args(argv)
    Handler.modello = a.modello
    S.sessione(a.modello, log=lambda *x: print(*x, file=sys.stderr))   # scalda prima di aprire
    srv = ThreadingHTTPServer((a.host, a.porta), Handler)
    print(f"pronto su http://{a.host}:{a.porta}  (Ctrl+C per fermare)", file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nchiuso', file=sys.stderr)


if __name__ == '__main__':
    main()
