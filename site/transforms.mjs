// Pattern transforms: upgrade recognizable Markdown structures to visual
// components (cards, steps, tiles, callouts, advice boxes).
//
// Hints: an HTML comment in the Markdown source forces a transform for the
// NEXT block and is invisible on GitHub. Supported hints:
//   <!-- site:cards -->   table -> card grid (columns: link, audience, topic)
//   <!-- site:steps -->   ordered list -> numbered step path
//   <!-- site:tiles -->   ordered list  -> tile grid (items like "**Title.** text")
//   <!-- site:callout --> blockquote/paragraph -> callout box
//   <!-- site:hide -->    next block is omitted from the site
// Without a hint, the heuristics in build.mjs decide. Unrecognized content
// falls back to plain marked rendering, so a structure change never breaks
// the page - it only renders less fancy.
import { marked } from 'marked';

/**
 * Escapes HTML special characters in raw text.
 * @param {string} text Raw text.
 * @returns {string} HTML-safe text.
 */
export function escapeHtml(text) {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

/**
 * Maps an audience label to a badge CSS class.
 * @param {string} label Audience label, e.g. "Bestuur" or "Security, beheer".
 * @returns {string} CSS class string.
 */
function badgeClass(label) {
  const key = label.toLowerCase();
  const bestuurlijk = ['bestuur', 'ciso', 'management', 'allen'];
  return bestuurlijk.some((b) => key.includes(b)) ? 'badge badge-bestuur' : 'badge badge-techniek';
}

/**
 * Renders comma-separated audience labels as badge spans.
 * @param {string} cell Raw audience cell text.
 * @returns {string} Badge HTML.
 */
export function renderBadges(cell) {
  return cell
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
    .map((l) => `<span class="${badgeClass(l)}">${escapeHtml(l)}</span>`)
    .join('');
}

/**
 * Renders a contents table (link | audience | topic) as a card grid.
 * @param {object} token Marked table token.
 * @param {Map<string, {num: string, title: string, id: string}>} chapterMeta Slug-to-chapter map.
 * @returns {string} Card grid HTML.
 */
export function cardsFromTable(token, chapterMeta) {
  const cards = token.rows.map((row, i) => {
    const link = row[0].text.match(/\[(.+?)\]\((.+?)\)/);
    if (!link) return '';
    const slug = link[2].replace(/\.md$/, '').replace(/\/$/, '');
    const meta = chapterMeta.get(slug);
    if (!meta) return '';
    return [
      `<a class="card" href="#${meta.id}" style="--d:${i}">`,
      `<span class="card-num">${escapeHtml(meta.num)}</span>`,
      `<span class="card-title">${escapeHtml(meta.title)}</span>`,
      `<span class="card-desc">${marked.parseInline(row[2].text)}</span>`,
      `<span class="card-badges">${renderBadges(row[1].text)}</span>`,
      `</a>`,
    ].join('');
  });
  return `<div class="cards">${cards.join('\n')}</div>`;
}

/**
 * Renders an ordered list as a numbered step path.
 * @param {object} token Marked list token.
 * @returns {string} Step list HTML.
 */
export function stepsFromList(token) {
  const items = token.items
    .map((it) => `<li><span class="step-body">${marked.parseInline(it.text)}</span></li>`)
    .join('\n');
  return `<ol class="steps">${items}</ol>`;
}

/**
 * Renders an ordered list of "**Title.** text" items as a tile grid.
 * @param {object} token Marked list token.
 * @returns {string} Tile grid HTML.
 */
export function tilesFromList(token) {
  const tiles = token.items.map((it, i) => {
    const m = it.text.match(/^\*\*(.+?)\*\*\s*([\s\S]*)$/);
    const title = m ? m[1].replace(/\.\s*$/, '') : `Punt ${i + 1}`;
    const body = m ? m[2] : it.text;
    return [
      `<div class="tile" style="--d:${i}">`,
      `<span class="tile-num">${i + 1}</span>`,
      `<h3>${marked.parseInline(title)}</h3>`,
      `<p>${marked.parseInline(body.replace(/\n/g, ' '))}</p>`,
      `</div>`,
    ].join('');
  });
  return `<div class="tiles">${tiles.join('\n')}</div>`;
}

/**
 * Renders a blockquote token as a callout box.
 * @param {object} token Marked blockquote token.
 * @returns {string} Callout HTML.
 */
export function calloutFromBlockquote(token) {
  return `<div class="callout">${marked.parser(token.tokens)}</div>`;
}

/**
 * Renders a "**Advies:** ..." paragraph as an advice box.
 * @param {object} token Marked paragraph token.
 * @returns {string} Advice box HTML.
 */
export function adviceFromParagraph(token) {
  const body = token.text.replace(/^\*\*Advies:\*\*\s*/, '');
  return [
    `<div class="advies"><span class="advies-label">Advies</span>`,
    `<p>${marked.parseInline(body.replace(/\n/g, ' '))}</p></div>`,
  ].join('');
}

/**
 * Renders a chapter H1 like "00 · Title" as a numbered chapter header.
 * @param {object} token Marked heading token (depth 1).
 * @returns {string} Chapter header HTML.
 */
export function chapterHeading(token) {
  const m = token.text.match(/^(\d{2})\s*·\s*(.+)$/);
  if (!m) return `<h1>${marked.parseInline(token.text)}</h1>`;
  return [
    `<header class="chapter-head"><span class="chapter-num">${m[1]}</span>`,
    `<h1>${marked.parseInline(m[2])}</h1></header>`,
  ].join('');
}
