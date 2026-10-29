# Usage: python3 -I extract.py <panel.html> <dumpdir> <out.json>
import json, os, sys
from playwright.sync_api import sync_playwright
panel, dump, out = sys.argv[1:4]
def col(name):
    d = os.path.join(dump, name); r = []
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith('.json'):
                r.append({'id': f[:-5], 'data': json.load(open(os.path.join(d, f)))})
    return r
DB = {c: col(c) for c in ['documentos','terminais','pacotes','config','meta','escopo']}
mock = """
(() => {
const DB = %s;
const snapDocs = arr => ({docs: arr.map(x => ({id: x.id, data: () => structuredClone(x.data), exists: true}))});
function Q(name, filters){ return {
  where(f, op, v){ return Q(name, [...filters, [f, op, v]]); },
  limit(){ return this; }, orderBy(){ return this; },
  onSnapshot(cb){ let arr = (DB[name] || []);
    for (const [f, op, v] of filters) arr = arr.filter(x => op === '==' ? x.data[f] === v : op === 'not-in' ? !v.includes(x.data[f]) : op === 'in' ? v.includes(x.data[f]) : true);
    setTimeout(() => cb(snapDocs(arr)), 0); return () => {}; },
  doc(id){ return D(name + '/' + id); } }; }
function D(path){ const [c, id] = path.split('/'); return {
  onSnapshot(cb){ const x = (DB[c] || []).find(y => y.id === id); setTimeout(() => cb({exists: !!x, id, data: () => x ? structuredClone(x.data) : undefined}), 0); return () => {}; },
  get: async () => { const x = (DB[c] || []).find(y => y.id === id); return {exists: !!x, data: () => x && x.data}; } }; }
const db = {collection: n => Q(n, []), doc: p => D(p)};
window.claude = {use: async n => n === 'db' ? db : null};
})();
""" % json.dumps(DB)
with sync_playwright() as p:
    b = p.chromium.launch(**({'executable_path':'/opt/pw-browsers/chromium'} if __import__('os').path.exists('/opt/pw-browsers/chromium') else {})); pg = b.new_context(timezone_id='America/Sao_Paulo', locale='pt-BR').new_page()
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('**/*', lambda r: r.abort() if r.request.url.startswith('http') else r.continue_())
    pg.add_init_script(mock)
    pg.goto('file://' + os.path.abspath(panel))
    pg.wait_for_timeout(2500)
    pg.click('[data-tab="and"]'); pg.wait_for_timeout(800)
    pg.click('[data-andall="1"]'); pg.wait_for_timeout(800)
    res = pg.evaluate("""() => {
      const sec = document.querySelector('#andSec');
      const hint = sec.querySelector('.and-top .hint')?.textContent || '';
      const header = sec.querySelector('.andh')?.outerHTML || '';
      const blocos = [...sec.querySelectorAll('[data-andb]')].filter(b => b.dataset.andb).map(b => ({b: b.dataset.andb, label: b.textContent.trim()}));
      const leg = sec.querySelector('.and-leg')?.innerHTML || '';
      const sitLabels = Object.fromEntries([...sec.querySelectorAll('[data-ands]')].filter(b => b.dataset.ands).map(b => [b.dataset.ands, b.firstChild.textContent.trim()]));
      const terms = [...sec.querySelectorAll('section.and-t')].map(s => ({
        terminal: s.querySelector('.panel-h h2').textContent,
        hint: s.querySelector('.panel-h .hint').textContent, obs: s.querySelector('.and-obs')?.textContent || '',
        discs: [...s.querySelectorAll('.and-d')].map(d => { const k = d.querySelector('[data-andx]').dataset.andx; return {
          dn: k.slice(k.indexOf('|') + 1), na: d.dataset.andna === '1', ek: d.dataset.andk || '',
          docs: [...d.querySelectorAll('tbody tr')].map(tr => { const td = tr.querySelectorAll('td'); const tag = td[3].querySelector('.tag');
            return {cod: td[0].textContent, tit: td[1].textContent, rev: td[2].textContent, k: tag.classList.contains('t-sp') ? 'sp' : tag.classList.contains('t-ok') ? 'ok' : tag.classList.contains('t-bas') ? 'bas' : 'dev', sit: td[3].innerHTML, env: td[4].innerHTML}; }) }; }) }));
      return {hint, header, blocos, leg, sitLabels, terms};
    }""")
    res['errors'] = errs
    b.close()
json.dump(res, open(out, 'w'), ensure_ascii=False)
n = sum(len(d['docs']) for t in res['terms'] for d in t['discs'])
print('terminais', len(res['terms']), 'docs', n, 'errs', errs[:3]); print(res['hint']); print(res['blocos']); print(res['sitLabels'])
