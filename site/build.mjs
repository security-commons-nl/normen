// Gedeeld build-script: gedeeld tussen Handelingsperspectief, ai-gebruik-in-beeld en
// csir-assessment-tool; wijzig ze samen.
// Dit bestand bevat geen repo-specifieke gegevens. Alles wat per repo verschilt (titel,
// beschrijving, repo-URL, hoofdstukken, query's) staat in site/config.json.
//
// Zet de Markdown-hoofdstukken en KQL-query's om in één statische index.html met
// tabnavigatie en visuele componenten. Uitvoer: dist/.
import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { marked } from 'marked';

import {
  escapeHtml, cardsFromTable, stepsFromList, tilesFromList,
  calloutFromBlockquote, adviceFromParagraph, chapterHeading,
} from './transforms.mjs';

const SITE_DIR = dirname(fileURLToPath(import.meta.url));
const ROOT = join(SITE_DIR, '..');

/**
 * Repo-specifieke configuratie uit site/config.json:
 *   repoUrl     GitHub-URL van de repo (voor licentie- en bronlinks)
 *   title       <title> van de pagina
 *   description meta description
 *   siteTitle   naam in de kopregel
 *   tabs        tabmanifest: bronbestand, stabiel section-id, korte tablabel, kaarttitel
 *   queryFiles  optioneel: KQL-bestanden in queries/, in de volgorde van weergave
 *   assets      optioneel: bestanden die ongewijzigd naar dist/ gaan (downloads)
 */
const CONFIG = JSON.parse(readFileSync(join(SITE_DIR, 'config.json'), 'utf8'));
const { repoUrl: REPO_URL, tabs: TABS, queryFiles: QUERY_FILES = [], assets: ASSETS = [] } = CONFIG;
const HAS_QUERIES = QUERY_FILES.length > 0;

/** Slug -> {num, title, id} map used by the card transform. */
const CHAPTER_META = new Map(
  TABS.filter((t) => t.title).map((t) => [t.id, { num: t.id.slice(0, 2), title: t.title, id: t.id }]),
);
if (HAS_QUERIES) CHAPTER_META.set('queries', { num: 'KQL', title: "Herbruikbare query's", id: 'queries' });

/**
 * Reads a site hint from an HTML-comment token.
 * @param {object} token Marked token.
 * @returns {string|null} Hint name or null.
 */
function readHint(token) {
  if (token.type !== 'html') return null;
  const m = token.text.match(/<!--\s*site:([a-z]+)\s*-->/);
  return m ? m[1] : null;
}

/**
 * Renders one Markdown token, applying a hint or heuristics where they match.
 * @param {object} token Marked token.
 * @param {{hint: string|null, lastH2: string, afterH1: boolean}} ctx Render context.
 * @returns {string} HTML for this token.
 */
function renderToken(token, ctx) {
  if (token.type === 'heading' && token.depth === 1) return chapterHeading(token);
  if (token.type === 'paragraph' && ctx.afterH1) {
    return `<p class="lead">${marked.parseInline(token.text.replace(/\n/g, ' '))}</p>`;
  }
  if (token.type === 'table') {
    const isContents = ctx.hint === 'cards'
      || token.header.some((h) => h.text.toLowerCase().includes('voor wie'));
    if (isContents) return cardsFromTable(token, CHAPTER_META);
    return `<div class="tablewrap">${marked.parser([token])}</div>`;
  }
  if (token.type === 'list' && token.ordered) {
    if (ctx.hint === 'steps' || ctx.lastH2.startsWith('volgorde')) return stepsFromList(token);
    if (ctx.hint === 'tiles' || ctx.lastH2.startsWith('drie uitgangspunten')) return tilesFromList(token);
  }
  if (token.type === 'blockquote' || ctx.hint === 'callout') {
    if (token.type === 'blockquote') return calloutFromBlockquote(token);
    return `<div class="callout">${marked.parser([token])}</div>`;
  }
  if (token.type === 'paragraph' && token.text.startsWith('**Advies:**')) {
    return adviceFromParagraph(token);
  }
  return marked.parser([token]);
}

/**
 * Renders a chapter's Markdown to section body HTML via the token walker.
 * @param {string} markdown Raw Markdown.
 * @returns {string} Section body HTML.
 */
function renderBody(markdown) {
  const tokens = marked.lexer(markdown, { gfm: true });
  const ctx = { hint: null, lastH2: '', afterH1: false };
  let html = '';
  for (const token of tokens) {
    const hint = readHint(token);
    if (hint) { ctx.hint = hint; continue; }
    if (ctx.hint === 'hide' && token.type !== 'space') { ctx.hint = null; continue; }
    if (token.type === 'space') continue;
    if (token.type === 'heading' && token.depth === 2) ctx.lastH2 = token.text.toLowerCase();
    html += renderToken(token, ctx);
    ctx.afterH1 = token.type === 'heading' && token.depth === 1;
    ctx.hint = null;
  }
  return html;
}

/**
 * Rewrites relative repo links in rendered HTML to in-page tab anchors.
 * Every source file from the tab manifest maps to its own tab; links into queries/ go to the
 * queries tab; LICENSE goes to the repo.
 * @param {string} html Rendered chapter HTML.
 * @returns {string} HTML with rewritten hrefs.
 */
function rewriteLinks(html) {
  let out = html;
  for (const t of TABS) {
    out = out.replaceAll(`href="${t.file}"`, `href="#${t.id}"`);
  }
  return out
    .replace(/href="queries\/[^"]*"/g, 'href="#queries"')
    .replace(/href="LICENSE"/g, `href="${REPO_URL}/blob/main/LICENSE"`);
}

/**
 * Extracts the "Doel:" sentence from a KQL file's leading comment block.
 * @param {string} source Raw KQL file content.
 * @returns {string} Short purpose description, or an empty string.
 */
function queryPurpose(source) {
  const header = [];
  for (const line of source.split('\n')) {
    if (!line.startsWith('//')) break;
    header.push(line.replace(/^\/\/\s?/, '').trim());
  }
  const text = header.join(' ');
  const match = text.match(/Doel:\s*(.*?)\s*(?:Vereist:|Bewuste beperkingen|$)/);
  return match ? match[1].trim() : '';
}

/**
 * Builds the HTML for the queries tab: one expandable card per KQL file.
 * @returns {string} Section inner HTML.
 */
function buildQueriesSection() {
  const blocks = QUERY_FILES.map((name, i) => {
    const source = readFileSync(join(ROOT, 'queries', name), 'utf8').trimEnd();
    const purpose = queryPurpose(source);
    return [
      `<article class="query" style="--d:${i}">`,
      `<h2><code>${escapeHtml(name)}</code></h2>`,
      purpose ? `<p class="query-doel">${escapeHtml(purpose)}</p>` : '',
      `<details><summary>Toon query</summary>`,
      `<div class="codewrap"><button class="copy" type="button" data-copy>Kopieer</button>`,
      `<pre><code>${escapeHtml(source)}</code></pre></div></details>`,
      `</article>`,
    ].join('\n');
  });
  return [
    `<header class="chapter-head"><span class="chapter-num">KQL</span><h1>Herbruikbare query's</h1></header>`,
    `<p class="lead">Voor Microsoft Defender Advanced Hunting. Pas parent-processen en uitsluitingen aan op je`,
    ` eigen omgeving; de toelichting staat in de commentaarregels van elke query.</p>`,
    ...blocks,
  ].join('\n');
}

/**
 * Assembles the complete index.html document.
 * @returns {string} Full HTML document.
 */
function buildPage() {
  const css = ['base.css', 'components.css']
    .map((f) => readFileSync(join(SITE_DIR, f), 'utf8')).join('\n');
  const js = readFileSync(join(SITE_DIR, 'page.js'), 'utf8');
  const allTabs = HAS_QUERIES ? [...TABS, { id: 'queries', label: "Query's" }] : TABS;
  const nav = allTabs
    .map((t) => `<button type="button" class="tab" data-target="${t.id}">${escapeHtml(t.label)}</button>`)
    .join('\n');
  const sections = [
    ...TABS.map((t) => {
      const body = rewriteLinks(renderBody(readFileSync(join(ROOT, t.file), 'utf8')));
      return `<section id="${t.id}" class="tab-panel" aria-label="${escapeHtml(t.label)}">\n${body}\n</section>`;
    }),
    ...(HAS_QUERIES
      ? [`<section id="queries" class="tab-panel" aria-label="Query's">\n${buildQueriesSection()}\n</section>`]
      : []),
  ].join('\n');
  return `<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(CONFIG.title)}</title>
<meta name="description" content="${escapeHtml(CONFIG.description)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="alternate icon" href="/favicon.ico" sizes="32x32">
<style>
${css}
</style>
</head>
<body>
<header class="site-header">
  <div class="inner masthead">
    <nav class="site-kicker" aria-label="Kruimelpad"><a href="https://security-commons-nl.github.io/">Security Commons NL</a> ›</nav>
    <span class="site-title">${escapeHtml(CONFIG.siteTitle)}</span>
  </div>
  <nav class="tabs inner" aria-label="Hoofdstukken">
${nav}
  </nav>
</header>
<main class="inner">
${sections}
</main>
<footer class="inner">
  <p>Licentie: <a href="${REPO_URL}/blob/main/LICENSE">EUPL-1.2</a> ·
     Bron en wijzigingsgeschiedenis: <a href="${REPO_URL}">GitHub</a> ·
     Deze pagina wordt automatisch gegenereerd uit de Markdown-bron.</p>
</footer>
<script>
${js}
</script>
</body>
</html>
`;
}

mkdirSync(join(ROOT, 'dist'), { recursive: true });
writeFileSync(join(ROOT, 'dist', 'index.html'), buildPage());
writeFileSync(join(ROOT, 'dist', '.nojekyll'), '');
// Downloads (zoals het werkboek) gaan ongewijzigd mee; anders wijst de knop op de pagina nergens heen.
for (const asset of ASSETS) {
  const naam = asset.split('/').pop();
  mkdirSync(dirname(join(ROOT, 'dist', asset)), { recursive: true });
  copyFileSync(join(ROOT, asset), join(ROOT, 'dist', asset));
  console.log(`Copied ${naam}`);
}
console.log('Wrote dist/index.html');
