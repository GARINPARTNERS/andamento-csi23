# Usage: python3 -I build.py <panel.html> <and.json> <out.html>
import json, re, sys
panel, src, out = sys.argv[1:4]
P = open(panel, encoding='utf-8').read()
m = re.search(r'<style>\n(/\* Layout: painel operacional.*?)</style>', P, re.S)
css = m.group(1)
R = json.load(open(src, encoding='utf-8'))
import hashlib, datetime, zoneinfo
from html import escape
from html.parser import HTMLParser
# O HTML vindo do painel é filtrado: só tags/atributos conhecidos passam (sem script, eventos, links ou url() externos).
OK_TAGS = {'span','div','b','i','em','strong','br','img','header','h1'}
OK_ATTRS = {'class','style','id','alt','title'}
VOID = {'br','img'}
DROP = ('script','style','iframe','object','embed','svg','math','template')
class Limpa(HTMLParser):
    def __init__(s): super().__init__(convert_charrefs=True); s.o = []; s.pilha = []; s.pula = 0
    def handle_starttag(s, tag, attrs):
        if tag in DROP: s.pula += 1; return
        if s.pula or tag not in OK_TAGS: return
        a = []
        for k, v in attrs:
            v = v or ''
            if k == 'src' and tag == 'img':
                if re.match(r'data:image/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+$', v): a.append(f' src="{v}"')
            elif k in OK_ATTRS:
                if k == 'style' and re.search(r'url\(|expression|javascript|@import|behavior', v, re.I): continue
                a.append(f' {k}="{escape(v, quote=True)}"')
        s.o.append(f'<{tag}{"".join(a)}>')
        if tag not in VOID: s.pilha.append(tag)
    def handle_endtag(s, tag):
        if tag in DROP: s.pula = max(0, s.pula - 1); return
        if s.pula: return
        if tag in s.pilha:
            while s.pilha:
                t = s.pilha.pop(); s.o.append(f'</{t}>')
                if t == tag: break
    def handle_data(s, d):
        if not s.pula: s.o.append(escape(d, quote=False))
    def close(s):
        super().close()
        while s.pilha: s.o.append(f'</{s.pilha.pop()}>')
def limpa(h):
    p = Limpa(); p.feed(h or ''); p.close(); return ''.join(p.o)
for t in R['terms']:
    for x in t['discs']:
        for d in x['docs']:
            d['sit'] = limpa(d['sit']); d['env'] = limpa(d['env'])
R['header'] = limpa(R.get('header'))
for t in R['terms']:
    if not t.get('obs'): t.pop('obs', None)
    for x in t['discs']:
        if not x.get('na'): x.pop('na', None)
        if not x.get('ek'): x.pop('ek', None)
core = json.dumps({'blocos': R['blocos'], 'sit': R['sitLabels'], 'terms': R['terms'], 'hdr': re.sub(r'<b id="and(Atu|Hoje)">[^<]*</b>', '', R.get('header') or '')}, ensure_ascii=False, sort_keys=True)
sha = hashlib.sha256(core.encode()).hexdigest()[:16]
now = datetime.datetime.now(zoneinfo.ZoneInfo('America/Sao_Paulo'))
DIAS = ['segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado','domingo']
upd = f"{DIAS[now.weekday()]}, {now:%d/%m/%Y} às {now:%H:%M}"
HDR = re.sub(r'(<b id="andAtu">)[^<]*(</b>)', lambda m: m.group(1) + f"{now:%d/%m/%Y %H:%M}" + m.group(2), R.get('header') or '')
if not HDR: sys.exit('cabeçalho da aba Andamento não encontrado no extract')
data = json.dumps({'upd': upd, 'blocos': R['blocos'], 'sit': R['sitLabels'], 'terms': R['terms']}, ensure_ascii=False).replace('</', '<\\/')
html = '<!-- andamento-sha:' + sha + ' -->\n' + '''<title>Andamento Projetos Executivos</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Barlow:wght@400;500;600&family=Barlow+Condensed:wght@700&display=swap">
<style>
''' + css + '''
/* página pública de andamento */
.pub-h{display:flex;flex-wrap:wrap;gap:10px 24px;align-items:flex-end;justify-content:space-between;padding-bottom:16px;border-bottom:1px solid var(--line)}
.pub-h h1{font-size:clamp(22px,3vw,32px);font-weight:800;line-height:1.08}
.pub-h .sub{color:var(--ink-2);margin-top:6px}
.pub-upd{font:500 12.5px var(--f-mono);color:var(--ink-2)}
.pub-upd b{color:var(--ink);font-weight:600}
#andSec{padding:16px}
@media (max-width:560px){#andSec{padding:12px 10px}.dtab th,.dtab td{padding:6px 6px}}
.pub-foot{font-size:12px;color:var(--ink-3)}
.andh{border-radius:0;margin:0}.andh-in{max-width:1320px;margin:0 auto}
</style>
''' + HDR + '''
<div class="wrap">
  <section class="panel" id="andSec"></section>
  <p class="pub-foot">Página somente para consulta. Atualizada automaticamente a partir do painel de controle dos projetos executivos.</p>
</div>
<script>
(() => {
const D = ''' + data + ''';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const nk = s => (s||'').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().replace(/\\s+/g,' ').trim();
const plural = (n, a, b) => `${n} ${n === 1 ? a : b}`;
const discLabel = n => { const m = n.match(/^([A-Z]{2,4})\\s*-\\s*(.+)$/); return m ? `<span class="mono" style="color:var(--ink-3);font-size:11.5px">${esc(m[1])}</span> ${esc(m[2])}` : esc(n); };
const ORD = ['sp','ok','dev','bas'].filter(k => D.sit[k]), CLS = {sp:'t-sp', ok:'t-ok', dev:'t-dev', bas:'t-bas'};
const SL = D.sit, SLp = {sp: (SL.sp||'').replace(/^Enviado/, 'enviados'), ok: (SL.ok||'').replace(/^Aprovado/, 'aprovados'), dev: 'em desenvolvimento', bas: 'aguardando aprovação do projeto básico'};
const C = (SL.sp || 'Enviado à SPTrans').replace(/^Enviado à /, '');
const store = (k, v) => { try { v === undefined ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch(e){} };
const load = k => { try { return localStorage.getItem(k); } catch(e){ return null; } };
let B = load('pubBloco') || '', T = '', S = '';
let OPEN = new Set(); try { OPEN = new Set(JSON.parse(load('pubAbertos') || '[]')); } catch(e){}
const saveOpen = () => store('pubAbertos', JSON.stringify([...OPEN]));
const blocoOf = t => (t.hint.match(/^Bloco ([A-Z])/) || [,''])[1];
(() => { const h = document.getElementById('andHoje'), n = new Date(); if (h) h.textContent = n.toLocaleDateString('pt-BR'); })();
function cnt(arr){ const c = {sp:0, ok:0, dev:0, bas:0}; arr.forEach(d => c[d.k]++); return c; }
const bar = (c, n) => n ? `<span class="sbar" role="img" aria-label="${esc(ORD.map(k => SL[k] + ': ' + c[k]).join(' · '))}" title="${esc(ORD.map(k => SL[k] + ': ' + c[k]).join(' · '))}">${ORD.map(k => c[k] ? `<i class="${CLS[k]}" style="width:${(c[k]/n*100).toFixed(2)}%"></i>` : '').join('')}</span>` : '';
const tags = c => ORD.filter(k => c[k]).map(k => `<span class="tag ${CLS[k]}"><b>${c[k]}</b> ${esc(SLp[k])}</span>`).join('');
const pct = (c, n) => n ? Math.round((c.sp + c.ok) / n * 100) : 0;
function render(){
  const el = document.getElementById('andSec');
  if (B && !D.blocos.some(x => x.b === B)) B = '';
  const tB = D.terms.filter(t => !B || blocoOf(t) === B);
  if (T && !tB.some(t => nk(t.terminal) === nk(T))) T = '';
  const ts = tB.filter(t => !T || nk(t.terminal) === nk(T));
  const all = ts.flatMap(t => t.discs.flatMap(d => d.docs)), cA = cnt(all);
  const row = d => `<tr><td class="nw mono">${esc(d.cod)}</td><td><div class="t" style="min-width:180px">${esc(d.tit || d.cod)}</div></td><td class="nw mono">${esc(d.rev || '—')}</td><td>${d.sit}</td><td class="nw">${d.env}</td></tr>`;
  const card = t => {
    const arr = t.discs.flatMap(d => d.docs), c = cnt(arr), n = arr.length;
    const discs = t.discs.map(x => {
      const k = t.terminal + '|' + x.dn, op = OPEN.has(k);
      const ek = x.ek || (x.na ? 'na' : 'dev');
      if (!x.docs.length) { if (S && S !== ek) return '';
        return `<div class="and-d"><button type="button" class="and-dh" data-x="${esc(k)}" aria-expanded="${op}"><span class="chev" aria-hidden="true">▶</span><span class="dn">${discLabel(x.dn)}</span><span class="and-tags">${ek === 'na' ? '<span class="tag t-na">Não se aplica</span>' : `<span class="tag ${CLS[ek] || 't-dev'}">${esc(SL[ek] || SL.dev)}</span>`}</span><span class="n">0</span></button>
        <div class="and-db"${op ? '' : ' hidden'}><div class="m" style="padding:4px 0 2px">${ek === 'na' ? 'Disciplina fora do escopo deste local.' : 'Nenhum documento emitido ainda nesta disciplina.'}</div></div></div>`; }
      const vis = x.docs.filter(d => !S || d.k === S); if (!vis.length) return '';
      const c2 = cnt(x.docs);
      return `<div class="and-d"><button type="button" class="and-dh" data-x="${esc(k)}" aria-expanded="${op}"><span class="chev" aria-hidden="true">▶</span><span class="dn">${discLabel(x.dn)}</span>${bar(c2, x.docs.length)}<span class="and-tags">${tags(c2)}</span><span class="n">${x.docs.length}</span></button>
        <div class="and-db"${op ? '' : ' hidden'}><div class="tscroll"><table class="dtab"><thead><tr><th>Código</th><th>Documento</th><th>Rev. atual</th><th>Situação</th><th>Protocolo · envio</th></tr></thead><tbody>${vis.map(row).join('')}</tbody></table></div></div></div>`; }).join('');
    if (S && !discs) return '';
    return `<section class="panel and-t"><div class="panel-h"><div><h2 style="display:inline">${esc(t.terminal)}</h2>${t.obs ? `<span class="and-obs">${esc(t.obs)}</span>` : ''}</div><span class="hint">${esc(t.hint)}</span></div>
      ${n ? `<div class="and-sum"><span class="big">${n}</span><span style="color:var(--ink-2)">documentos</span>${bar(c, n)}<span class="pct"><b>${pct(c, n)}%</b> já enviados à ${esc(C)}</span><span class="and-tags">${tags(c)}</span></div>`
        : `<div class="empty" style="padding:14px 16px">Nenhum documento do projeto executivo emitido ainda.</div>`}${discs}</section>`; };
  const body = ts.map(card).join('');
  el.innerHTML = `<div class="and-top"><div class="hint">Situação de cada documento do projeto executivo por terminal e disciplina. Clique na disciplina para ver os documentos.</div>
    <div class="and-bar"><div class="and-f"><div class="tpills" role="group" aria-label="Filtrar por bloco"><span class="eyebrow" style="margin-right:4px">Bloco</span><button type="button" data-b="" aria-pressed="${!B}">Todos</button>${D.blocos.map(x => `<button type="button" data-b="${esc(x.b)}" aria-pressed="${B===x.b}">${esc(x.label)}</button>`).join('')}</div>
      <label class="cpe-sel"><span class="eyebrow">Terminal</span><select data-t><option value="">Todos</option>${tB.map(t => `<option value="${esc(t.terminal)}"${nk(T) === nk(t.terminal) ? ' selected' : ''}>${esc(t.terminal)}</option>`).join('')}</select></label></div>
      <div style="display:flex;gap:6px;flex-wrap:wrap"><button class="btn small ghost" type="button" data-all="1">Expandir todas</button><button class="btn small ghost" type="button" data-all="0">Recolher todas</button></div></div>
    <div class="tpills" role="group" aria-label="Filtrar por situação"><span class="eyebrow" style="margin-right:4px">Situação</span><button type="button" data-s="" aria-pressed="${!S}">Todas<b>${all.length}</b></button>${ORD.map(k => `<button type="button" data-s="${k}" aria-pressed="${S===k}">${esc(SL[k])}<b>${cA[k]}</b></button>`).join('')}</div>
    ${all.length ? `<div class="panel"><div class="and-sum" style="border-bottom:0"><span class="big">${all.length}</span><span style="color:var(--ink-2)">documentos ${T ? 'neste terminal' : B ? 'no Bloco ' + esc(B) : 'no total'}</span>${bar(cA, all.length)}<span class="pct"><b>${pct(cA, all.length)}%</b> já enviados à ${esc(C)}</span><span class="and-tags">${tags(cA)}</span></div></div>` : ''}
    <p class="and-leg"><span><span class="tag t-sp">${esc(SL.sp)}</span> revisão protocolada na ${esc(C)}, aguardando retorno</span><span><span class="tag t-ok">${esc(SL.ok)}</span> aprovado pela ${esc(C)}</span><span><span class="tag t-dev">${esc(SL.dev)}</span> em elaboração ou ajuste pelo projetista, ou em análise técnica antes do envio</span>${SL.bas ? `<span><span class="tag t-bas">${esc(SL.bas)}</span> terminal aguardando a aprovação do projeto básico</span>` : ''}</p></div>
  <div class="and-grid">${body || '<div class="empty" style="padding:18px 16px">Nenhum documento com esse filtro.</div>'}</div>`;
}
document.addEventListener('change', e => { const s = e.target.closest && e.target.closest('select[data-t]'); if (s) { T = s.value; render(); } });
document.addEventListener('click', e => {
  if (!e.target.closest) return;
  const b = e.target.closest('[data-b]'); if (b) { B = b.dataset.b; T = ''; store('pubBloco', B); render(); return; }
  const s = e.target.closest('[data-s]'); if (s) { S = s.dataset.s; render(); return; }
  const x = e.target.closest('[data-x]'); if (x) { const k = x.dataset.x, op = !OPEN.has(k); op ? OPEN.add(k) : OPEN.delete(k); saveOpen(); x.setAttribute('aria-expanded', String(op)); const nx = x.nextElementSibling; if (nx) nx.hidden = !op; return; }
  const a = e.target.closest('[data-all]'); if (a) { document.querySelectorAll('#andSec [data-x]').forEach(y => a.dataset.all === '1' ? OPEN.add(y.dataset.x) : OPEN.delete(y.dataset.x)); saveOpen(); render(); }
});
render();
})();
</script>'''
open(out, 'w', encoding='utf-8').write(html)
print('sha', sha, 'bytes', len(html), 'docs', sum(len(d['docs']) for t in R['terms'] for d in t['discs']))
