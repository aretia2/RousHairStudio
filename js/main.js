/* LRS · Rou's Hair Studio — interacción de la página (sin dependencias). */
(() => {
  'use strict';
  document.documentElement.classList.add('js');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const smooth = (v) => { const t = clamp(v); return t * t * (3 - 2 * t); };

  /* ---------- Cabecera y menú ---------- */
  const header = $('[data-header]');
  const burger = $('[data-burger]');
  const nav = $('[data-nav]');
  const mobilebar = $('[data-mobilebar]');
  const hero = $('.hero');

  const onScroll = () => {
    const y = window.scrollY;
    header.classList.toggle('is-solid', y > 24);
    if (mobilebar && hero) mobilebar.classList.toggle('is-visible', y > hero.offsetHeight * 0.6);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  const setMenu = (open) => {
    burger.setAttribute('aria-expanded', String(open));
    burger.setAttribute('aria-label', open ? 'Cerrar menú' : 'Abrir menú');
    nav.classList.toggle('is-open', open);
    header.classList.toggle('menu-open', open);
    document.body.style.overflow = open ? 'hidden' : '';
  };
  burger?.addEventListener('click', () => setMenu(burger.getAttribute('aria-expanded') !== 'true'));
  nav?.addEventListener('click', (e) => { if (e.target.closest('a')) setMenu(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && nav.classList.contains('is-open')) { setMenu(false); burger.focus(); } });
  window.matchMedia('(min-width: 1024px)').addEventListener('change', (m) => m.matches && setMenu(false));

  // Sección actual en el menú
  const links = $$('.nav a[href^="#"]');
  const targets = links.map((a) => $(a.getAttribute('href'))).filter(Boolean);
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        links.forEach((a) => a.classList.toggle('is-current', a.getAttribute('href') === '#' + en.target.id));
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    targets.forEach((t) => io.observe(t));
  }

  /* ---------- Techo de hexágonos ---------- */
  const grid = $('[data-hexgrid]');
  if (grid) {
    const NS = 'http://www.w3.org/2000/svg';
    const R = 60; // separación (el dibujo es de radio 50: quedan huecos como en el techo real)
    const colStep = 1.5 * R;
    const rowStep = Math.sqrt(3) * R;
    const cells = [];
    for (let c = 0; c * colStep < 1200 + R; c++) {
      for (let r = 0; r * rowStep < 420 + R; r++) {
        const x = c * colStep;
        const y = r * rowStep + (c % 2 ? rowStep / 2 : 0);
        const u = document.createElementNS(NS, 'use');
        u.setAttribute('href', '#hx');
        u.setAttribute('x', String(x - 52));
        u.setAttribute('y', String(y - 45));
        u.setAttribute('width', '104');
        u.setAttribute('height', '90');
        grid.appendChild(u);
        cells.push({ u, x, y });
      }
    }
    // Las luces se encienden desde el centro hacia fuera, como un techo al darle al interruptor.
    const cx = 600;
    const order = cells
      .map((c) => ({ ...c, d: Math.hypot(c.x - cx, c.y - 40) + Math.random() * 140 }))
      .sort((a, b) => a.d - b.d);
    const lit = (c) => c.u.classList.add(Math.random() < 0.78 ? 'on' : 'half');
    if (reduced.matches) order.forEach(lit);
    else {
      order.forEach((c, i) => setTimeout(() => lit(c), 250 + i * 14 + (Math.random() < 0.15 ? 250 : 0)));

      // Ambiente: de vez en cuando una luz se atenúa suavemente y vuelve (o una tenue se aviva).
      // Sólo mientras la portada está en pantalla y la pestaña visible.
      const introEnd = 250 + order.length * 14 + 1800;
      let visible = true;
      const breathe = () => {
        if (!visible || document.hidden) return;
        const c = order[Math.floor(Math.random() * order.length)].u;
        if (c.classList.contains('dim') || c.classList.contains('glow')) return;
        const cls = c.classList.contains('on') ? 'dim' : 'glow';
        c.classList.add(cls);
        setTimeout(() => c.classList.remove(cls), 3200 + Math.random() * 3800);
      };
      setTimeout(() => {
        grid.classList.add('is-live');
        setInterval(breathe, 900);
      }, introEnd);
      if ('IntersectionObserver' in window) {
        new IntersectionObserver(([en]) => { visible = en.isIntersecting; }).observe(grid.closest('.hero') || grid);
      }
    }
  }

  /* ---------- Revelados ---------- */
  const reveals = $$('[data-reveal]');
  if ('IntersectionObserver' in window && !reduced.matches) {
    const ro = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('is-in'); ro.unobserve(en.target); } });
    }, { rootMargin: '0px 0px -8% 0px' });
    reveals.forEach((el) => ro.observe(el));
  } else reveals.forEach((el) => el.classList.add('is-in'));

  /* ---------- Secuencia de trabajos (fijada y ligada al scroll) ---------- */
  const seq = $('[data-seq]');
  if (seq && !reduced.matches) {
    const PER_FRAME = 1, HOLD = 0.6, STAGGER = 0.18;
    const sticky = $('[data-seq-sticky]', seq);
    const frames = $$('[data-frame]', seq);
    const panels = frames.map((li) => $$('[data-panel]', li));
    const count = $('[data-seq-count]', seq);
    const bar = $('[data-seq-bar]', seq);
    const shade = $('[data-seq-shade]', seq);
    const total = seq.dataset.total || '';
    let start = 0, run = 1, vh = innerHeight, target = 0, current = 0, raf = 0;

    const measure = () => {
      vh = innerHeight;
      run = Math.max(1, (frames.length - 1) * PER_FRAME * vh);
      seq.style.height = `${vh + run + HOLD * vh}px`;
      start = seq.getBoundingClientRect().top + scrollY;
    };
    const render = () => {
      current += (target - current) * 0.14;
      if (Math.abs(target - current) < 0.5) current = target;
      const t = frames.length > 1 ? clamp(current / run) : 1;
      const seg = t * (frames.length - 1);
      const ops = frames.map((_, i) => (i === 0 ? 1 : smooth(seg - (i - 1))));
      let active = 0, best = -1;
      frames.forEach((li, i) => {
        const scale = 1.18 - (0.18 * clamp(seg - i + 1, 0, 2)) / 2;
        panels[i].forEach((p, j) => {
          const o = i === 0 ? 1 : smooth((seg - (i - 1) - j * STAGGER) / (1 - 2 * STAGGER));
          p.style.setProperty('--o', o.toFixed(3));
          p.style.setProperty('--s', scale.toFixed(4));
        });
        const w = ops[i] * (1 - (ops[i + 1] ?? 0));
        li.style.setProperty('--w', smooth(w * 2.5 - 1.2).toFixed(3));
        if (w > best) { best = w; active = i; }
      });
      frames.forEach((li, i) => li.classList.toggle('is-active', i === active));
      seq.classList.toggle('is-last', active === frames.length - 1);
      if (count) count.textContent = `${frames[active].dataset.range} / ${total}`;
      bar?.style.setProperty('--p', t.toFixed(4));
      shade?.style.setProperty('--shade', (smooth((current - run - HOLD * vh * 0.3) / (HOLD * vh * 0.7)) * 0.75).toFixed(3));
      raf = current === target ? 0 : requestAnimationFrame(render);
    };
    const kick = () => { target = clamp(scrollY - start, 0, run + HOLD * vh); if (!raf) raf = requestAnimationFrame(render); };

    document.documentElement.classList.add('seq-on');
    measure();
    target = current = clamp(scrollY - start, 0, run + HOLD * vh);
    render();
    addEventListener('scroll', kick, { passive: true });
    let rt;
    addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { measure(); kick(); }, 120); });
    addEventListener('load', () => { measure(); kick(); });
    sticky.addEventListener('focusin', (e) => {
      const i = frames.findIndex((li) => li.contains(e.target));
      if (i < 0 || frames[i].classList.contains('is-active')) return;
      scrollTo({ top: start + (i / Math.max(1, frames.length - 1)) * run, behavior: 'auto' });
    });
  }

  /* ---------- Visor ---------- */
  const gallery = $('[data-gallery]');
  const dialog = $('[data-lightbox]');
  if (gallery && dialog && typeof dialog.showModal === 'function') {
    const img = $('[data-lb-img]', dialog);
    const cap = $('[data-lb-caption]', dialog);
    const cnt = $('[data-lb-count]', dialog);
    const btns = $$('[data-full]', gallery);
    let cur = 0, opener = null;
    const show = (i) => {
      cur = (i + btns.length) % btns.length;
      const b = btns[cur];
      img.src = b.dataset.full;
      img.alt = $('img', b)?.alt || '';
      cap.textContent = b.dataset.caption || '';
      cnt.textContent = `${String(cur + 1).padStart(2, '0')} / ${String(btns.length).padStart(2, '0')}`;
    };
    gallery.addEventListener('click', (e) => {
      const b = e.target.closest('[data-full]');
      if (!b) return;
      opener = b; show(btns.indexOf(b)); dialog.showModal(); document.body.style.overflow = 'hidden';
    });
    dialog.addEventListener('close', () => { document.body.style.overflow = ''; img.removeAttribute('src'); opener?.focus(); });
    $('[data-lb-close]', dialog).addEventListener('click', () => dialog.close());
    $('[data-lb-prev]', dialog).addEventListener('click', () => show(cur - 1));
    $('[data-lb-next]', dialog).addEventListener('click', () => show(cur + 1));
    dialog.addEventListener('click', (e) => { if (e.target === dialog || e.target.classList.contains('lb__figure')) dialog.close(); });
    dialog.addEventListener('keydown', (e) => { if (e.key === 'ArrowLeft') show(cur - 1); if (e.key === 'ArrowRight') show(cur + 1); });
    let sx = 0, sy = 0;
    dialog.addEventListener('touchstart', (e) => { sx = e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
    dialog.addEventListener('touchend', (e) => {
      const dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) show(cur + (dx < 0 ? 1 : -1));
    }, { passive: true });
  }

  /* ---------- Visagismo ---------- */
  const SHAPES = {
    ovalada: {
      p: { ty: 30, fw: 76, fy: 98, cw: 84, jw: 66, jy: 222, chw: 32, chy: 280 },
      title: 'Equilibrio natural',
      text: 'Proporciones equilibradas: es la forma que más estructuras admite. El trabajo está en elegir según tu pelo y tu estilo, no en corregir.',
      tips: ['<b>Casi todo funciona:</b> crop, texturizado, peinado hacia atrás o rizo.', '<b>Cuidado</b> con flequillos muy pesados que acorten la cara.', '<b>Degradado</b> a tu gusto: del taper suave al fade alto.'],
    },
    redonda: {
      p: { ty: 42, fw: 80, fy: 100, cw: 96, jw: 82, jy: 212, chw: 46, chy: 266 },
      title: 'Ganar altura y líneas',
      text: 'Anchura y altura parecidas, con contornos suaves. Se busca alargar visualmente y definir ángulos.',
      tips: ['<b>Volumen arriba</b>, laterales limpios (mid o high fade).', '<b>Evitar</b> masa en los laterales, que ensancha.', '<b>Barba</b> perfilada que marque mandíbula y alargue el mentón.'],
    },
    cuadrada: {
      p: { ty: 34, fw: 86, fy: 88, cw: 88, jw: 88, jy: 234, chw: 54, chy: 272 },
      title: 'Aprovechar la mandíbula',
      text: 'Frente, pómulos y mandíbula de anchura similar y ángulos marcados. Es una base muy masculina que solo hay que acompañar.',
      tips: ['<b>Textura arriba</b> para suavizar tanta línea recta.', '<b>Fade medio</b> o taper: limpio sin endurecer más.', '<b>Barba corta</b> o perfilado: deja que la mandíbula hable.'],
    },
    alargada: {
      p: { ty: 14, fw: 66, fy: 84, cw: 70, jw: 60, jy: 238, chw: 30, chy: 292 },
      title: 'Acortar sin perder forma',
      text: 'Más larga que ancha. El objetivo es equilibrar: menos altura y algo más de presencia en los laterales.',
      tips: ['<b>Evitar</b> tupés y mucha altura.', '<b>Flequillo</b> o crop hacia delante para acortar la frente.', '<b>Laterales</b> con algo de peso, sin raparlos al cero.'],
    },
    triangular: {
      p: { ty: 30, fw: 92, fy: 92, cw: 82, jw: 50, jy: 222, chw: 16, chy: 282 },
      title: 'Dar base al mentón',
      text: 'Frente ancha y barbilla estrecha (forma de corazón). Se trata de restar peso arriba y sumar abajo.',
      tips: ['<b>Textura</b> o flequillo ligero que cubra parte de la frente.', '<b>Sin volumen</b> excesivo en la coronilla.', '<b>Barba</b> que dé anchura a la mandíbula.'],
    },
    diamante: {
      p: { ty: 34, fw: 64, fy: 98, cw: 98, jw: 54, jy: 222, chw: 18, chy: 282 },
      title: 'Suavizar los pómulos',
      text: 'Pómulos anchos con frente y mentón estrechos. Funciona dar algo de anchura arriba y abajo.',
      tips: ['<b>Flequillo</b> o textura hacia delante para ensanchar la frente.', '<b>Laterales</b> no demasiado cortos a la altura del pómulo.', '<b>Barba</b> rellena en el mentón para equilibrar.'],
    },
  };
  // Contorno cerrado y suave (Catmull-Rom → Bézier) que pasa por frente, pómulo, mandíbula y mentón.
  const faceD = ({ ty, fw, fy, cw, jw, jy, chw, chy }) => {
    const X = 120, cy = 152;
    const pts = [
      [X, ty], [X + fw * 0.7, ty + (fy - ty) * 0.16], [X + fw, fy], [X + cw, cy], [X + jw, jy], [X + chw, chy - 6], [X, chy],
      [X - chw, chy - 6], [X - jw, jy], [X - cw, cy], [X - fw, fy], [X - fw * 0.7, ty + (fy - ty) * 0.16],
    ];
    const n = pts.length;
    const r = (v) => Math.round(v * 10) / 10;
    let d = `M${pts[0][0]},${pts[0][1]}`;
    for (let i = 0; i < n; i++) {
      const p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
      d += ` C${r(p1[0] + (p2[0] - p0[0]) / 6)},${r(p1[1] + (p2[1] - p0[1]) / 6)} ${r(p2[0] - (p3[0] - p1[0]) / 6)},${r(p2[1] - (p3[1] - p1[1]) / 6)} ${r(p2[0])},${r(p2[1])}`;
    }
    return d + 'Z';
  };
  const shapes = $('[data-shapes]');
  if (shapes) {
    const path = $('[data-face-path]');
    const marks = $('[data-face-marks]');
    const tag = $('[data-face-tag]');
    const tTitle = $('[data-visa-title]');
    const tText = $('[data-visa-text]');
    const tTips = $('[data-visa-tips]');
    const btns = $$('[data-shape]', shapes);
    const select = (key, focus) => {
      const s = SHAPES[key];
      btns.forEach((b) => {
        const on = b.dataset.shape === key;
        b.setAttribute('aria-checked', String(on));
        b.tabIndex = on ? 0 : -1;
        if (on && focus) b.focus();
      });
      path.setAttribute('d', faceD(s.p));
      const p = s.p;
      const row = (y, w, label) => `<line x1="${120 - w}" y1="${y}" x2="${120 + w}" y2="${y}"/><text x="${120 + w + 6}" y="${y + 3}">${label}</text>`;
      marks.innerHTML = row(p.fy, p.fw, 'F') + row(152, p.cw, 'P') + row(p.jy, p.jw, 'M');
      tag.textContent = btns.find((b) => b.dataset.shape === key).textContent;
      tTitle.textContent = s.title;
      tText.textContent = s.text;
      tTips.innerHTML = s.tips.map((t) => `<li><span>${t}</span></li>`).join('');
    };
    shapes.addEventListener('click', (e) => { const b = e.target.closest('[data-shape]'); if (b) select(b.dataset.shape); });
    shapes.addEventListener('keydown', (e) => {
      const i = btns.findIndex((b) => b.getAttribute('aria-checked') === 'true');
      const d = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
      if (!d) return;
      e.preventDefault();
      select(btns[(i + d + btns.length) % btns.length].dataset.shape, true);
    });
    select('ovalada');
  }

  /* ---------- Abierto ahora (hora de Tomares) ---------- */
  const HOURS = {
    0: [],
    1: [['15:20', '21:20']],
    2: [['11:00', '14:00'], ['15:20', '20:40']],
    3: [['10:40', '14:00'], ['15:20', '20:40']],
    4: [['10:00', '14:00'], ['15:20', '20:40']],
    5: [['10:00', '14:00'], ['15:20', '20:40']],
    6: [['09:40', '14:00']],
  };
  const DAYS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
  const mins = (hm) => { const [h, m] = hm.split(':').map(Number); return h * 60 + m; };
  const madridNow = () => {
    const parts = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Madrid', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false }).formatToParts(new Date());
    const get = (t) => parts.find((p) => p.type === t).value;
    const day = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(get('weekday'));
    return { day, m: (Number(get('hour')) % 24) * 60 + Number(get('minute')) };
  };
  const status = () => {
    const { day, m } = madridNow();
    const open = HOURS[day].find(([a, b]) => m >= mins(a) && m < mins(b));
    if (open) return { open: true, short: 'Abierto', long: `Abierto ahora · cierra a las ${open[1]}`, day };
    const later = HOURS[day].find(([a]) => mins(a) > m);
    if (later) return { open: false, short: 'Cerrado', long: `Cerrado ahora · abre hoy a las ${later[0]}`, day };
    for (let k = 1; k <= 7; k++) {
      const d = (day + k) % 7;
      if (HOURS[d].length) return { open: false, short: 'Cerrado', long: `Cerrado ahora · abre ${k === 1 ? 'mañana' : 'el ' + DAYS[d]} a las ${HOURS[d][0][0]}`, day };
    }
    return { open: false, short: 'Cerrado', long: 'Cerrado', day };
  };
  const paint = () => {
    const s = status();
    document.body.classList.toggle('is-open', s.open);
    document.body.classList.toggle('is-closed', !s.open);
    $$('[data-status-short]').forEach((el) => (el.textContent = s.short));
    const s2 = $('[data-status-short2]');
    if (s2) s2.textContent = s.open ? 'Abierto' : '24 h online';
    $$('[data-status-text]').forEach((el) => (el.textContent = s.long));
    const long = $('[data-status-long]');
    if (long) { long.classList.toggle('is-open', s.open); long.classList.toggle('is-closed', !s.open); $('span', long).textContent = s.long; }
    $$('[data-hours] tr').forEach((tr) => tr.classList.toggle('is-today', Number(tr.dataset.day) === s.day));
  };
  paint();
  setInterval(paint, 60000);

  /* ---------- Mapa bajo demanda ---------- */
  const mapBtn = $('[data-map-load]');
  mapBtn?.addEventListener('click', () => {
    const f = document.createElement('iframe');
    f.src = 'https://www.google.com/maps?q=Calle+Navarro+Caro+72,+41940+Tomares&z=17&output=embed';
    f.title = 'Mapa: Rou\'s Hair Studio, Calle Navarro Caro 72, Tomares';
    f.loading = 'lazy';
    f.referrerPolicy = 'no-referrer-when-downgrade';
    $('[data-map]').appendChild(f);
    $('.map__ph').remove();
  });
})();
