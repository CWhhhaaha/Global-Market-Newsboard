from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, time, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse

from .pipeline import NewsStreamService

service = NewsStreamService()


def parse_day_start(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.combine(datetime.fromisoformat(value).date(), time.min, tzinfo=timezone.utc)


def parse_day_end(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.combine(datetime.fromisoformat(value).date(), time.max, tzinfo=timezone.utc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(service.run_forever())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="Global Market Newsboard",
    description="Open-source real-time dashboard for global market-moving headlines and trader-facing signal boards.",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    return """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Global Market Newsboard</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f2f0ea;
        --panel: #fcfaf4;
        --panel-strong: #f7f3eb;
        --ink: #1c2228;
        --muted: #69707a;
        --border: #d7cfbf;
        --accent: #9a2e1a;
        --accent-soft: rgba(154, 46, 26, 0.08);
        --bull: #0b6b45;
        --bull-bg: rgba(11, 107, 69, 0.12);
        --bear: #a12626;
        --bear-bg: rgba(161, 38, 38, 0.12);
        --watch: #755d11;
        --watch-bg: rgba(117, 93, 17, 0.12);
      }
      body {
        margin: 0;
        padding: 24px;
        background:
          radial-gradient(circle at top right, rgba(154, 46, 26, 0.10), transparent 26%),
          linear-gradient(180deg, #f7f3eb 0%, var(--bg) 100%);
        font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
        color: var(--ink);
      }
      .wrap {
        max-width: 1560px;
        margin: 0 auto;
      }
      h1 {
        font-size: 40px;
        margin: 0 0 8px;
        letter-spacing: -0.03em;
      }
      p {
        margin: 0 0 20px;
        color: var(--muted);
        font-size: 16px;
      }
      .stream {
        display: grid;
        gap: 10px;
      }
      .panel-scroller {
        max-height: calc(100vh - 250px);
        overflow-y: auto;
        padding-right: 6px;
        scrollbar-width: thin;
      }
      .panel-scroller::-webkit-scrollbar {
        width: 8px;
      }
      .panel-scroller::-webkit-scrollbar-thumb {
        background: rgba(154, 46, 26, 0.22);
        border-radius: 999px;
      }
      .panel-scroller::-webkit-scrollbar-track {
        background: rgba(215, 207, 191, 0.25);
        border-radius: 999px;
      }
      .hero {
        display: flex;
        justify-content: space-between;
        gap: 18px;
        align-items: end;
        margin-bottom: 18px;
      }
      .hero-copy {
        max-width: 820px;
      }
      .hero-kpis {
        display: grid;
        grid-template-columns: repeat(3, minmax(120px, 1fr));
        gap: 10px;
      }
      .hero-side {
        display: grid;
        gap: 10px;
        align-items: start;
      }
      .language-box {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 10px;
      }
      .language-box label {
        font-size: 12px;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .language-box select {
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 9px 12px;
        background: rgba(255, 250, 241, 0.96);
        color: var(--ink);
        font: inherit;
      }
      .kpi {
        background: linear-gradient(180deg, rgba(255,250,241,0.95), rgba(244,237,226,0.95));
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 12px 14px;
      }
      .kpi-label {
        color: var(--muted);
        font-size: 12px;
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }
      .kpi-value {
        font-size: 20px;
        font-weight: 700;
      }
      .layout {
        display: grid;
        grid-template-columns: minmax(0, 1.75fr) minmax(320px, 0.8fr) minmax(320px, 0.95fr);
        gap: 16px;
        align-items: start;
      }
      .layout > * {
        min-width: 0;
      }
      .panel {
        background: rgba(255, 250, 241, 0.82);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 16px;
        box-shadow: 0 10px 28px rgba(31, 35, 40, 0.05);
        backdrop-filter: blur(6px);
      }
      .sticky-panel {
        position: sticky;
        top: 16px;
      }
      .panel h2 {
        margin: 0 0 8px;
        font-size: 18px;
        letter-spacing: 0.01em;
      }
      .panel-note {
        margin: 0 0 14px;
        color: var(--muted);
        font-size: 12px;
      }
      .subgrid {
        display: grid;
        gap: 14px;
      }
      .section-grid {
        display: grid;
        gap: 14px;
      }
      .toolbar {
        display: grid;
        grid-template-columns: 2fr 1fr 1fr 1fr 1fr auto auto;
        gap: 10px;
        margin: 0 0 20px;
      }
      .toolbar input,
      .toolbar select,
      .toolbar button {
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 10px 12px;
        font: inherit;
        background: rgba(255, 250, 241, 0.96);
        color: var(--ink);
      }
      .toolbar button {
        background: var(--accent);
        color: #fffaf1;
        cursor: pointer;
      }
      .toolbar button.alt {
        background: transparent;
        color: var(--accent);
      }
      .card {
        background: linear-gradient(180deg, var(--panel), var(--panel-strong));
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 14px 16px;
        box-shadow: 0 8px 20px rgba(31, 35, 40, 0.04);
      }
      .meta {
        color: var(--muted);
        font-size: 12px;
        margin-bottom: 8px;
      }
      .meta-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 10px;
        flex-wrap: wrap;
      }
      .meta-left,
      .meta-right,
      .badge-row {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
      }
      .title {
        font-size: 18px;
        line-height: 1.32;
        margin-bottom: 8px;
        overflow-wrap: anywhere;
        font-weight: 700;
      }
      .summary {
        font-size: 14px;
        line-height: 1.45;
        margin-bottom: 10px;
        overflow-wrap: anywhere;
        color: #2b333b;
      }
      .line {
        font-family: ui-monospace, "SFMono-Regular", monospace;
        font-size: 11px;
        white-space: pre-wrap;
        color: #38414c;
        overflow-wrap: anywhere;
        word-break: break-word;
      }
      .detail-line {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 8px;
        margin: 0 0 10px;
      }
      .detail-pill {
        background: rgba(255,255,255,0.45);
        border: 1px solid rgba(215, 207, 191, 0.95);
        border-radius: 10px;
        padding: 8px 10px;
      }
      .detail-label {
        font-size: 10px;
        color: var(--muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
      }
      .detail-value {
        font-size: 12px;
        font-weight: 600;
        overflow-wrap: anywhere;
      }
      .compact-list {
        display: grid;
        gap: 8px;
      }
      .compact-card {
        background: linear-gradient(180deg, var(--panel), var(--panel-strong));
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 10px 12px;
      }
      .section-card {
        background: linear-gradient(180deg, rgba(255,250,241,0.98), rgba(247,242,233,0.94));
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 14px;
      }
      .section-card h3 {
        margin: 0 0 10px;
        font-size: 15px;
        letter-spacing: 0.01em;
      }
      .compact-title {
        font-size: 14px;
        line-height: 1.35;
        margin-bottom: 5px;
        overflow-wrap: anywhere;
        font-weight: 650;
      }
      .compact-meta {
        font-size: 11px;
        color: var(--muted);
        margin-bottom: 6px;
        overflow-wrap: anywhere;
      }
      .badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        border-radius: 999px;
        padding: 4px 8px;
        font-size: 10px;
        line-height: 1;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        border: 1px solid transparent;
      }
      .badge-neutral {
        background: var(--accent-soft);
        color: var(--accent);
        border-color: rgba(154, 46, 26, 0.12);
      }
      .badge-bull {
        background: var(--bull-bg);
        color: var(--bull);
        border-color: rgba(11, 107, 69, 0.12);
      }
      .badge-bear {
        background: var(--bear-bg);
        color: var(--bear);
        border-color: rgba(161, 38, 38, 0.12);
      }
      .badge-watch {
        background: var(--watch-bg);
        color: var(--watch);
        border-color: rgba(117, 93, 17, 0.12);
      }
      .score {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 999px;
        background: rgba(154, 46, 26, 0.12);
        color: var(--accent);
        font-size: 11px;
        margin-bottom: 8px;
      }
      .tagline {
        display: inline-block;
        border-radius: 999px;
        padding: 5px 10px;
        font-size: 11px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        background: rgba(140, 47, 27, 0.09);
        color: var(--accent);
        margin-bottom: 12px;
      }
      .sync-note {
        color: var(--muted);
        font-size: 12px;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        flex-wrap: wrap;
      }
      .legend {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }
      a {
        color: var(--accent);
        overflow-wrap: anywhere;
      }
      .pager {
        display: flex;
        gap: 10px;
        align-items: center;
        margin: 0 0 18px;
        color: var(--muted);
        flex-wrap: wrap;
      }
      .pager button {
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 8px 12px;
        background: var(--panel);
        color: var(--ink);
        cursor: pointer;
        font: inherit;
      }
      .stream-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 10px;
        flex-wrap: wrap;
      }
      .stream-head .panel-note {
        margin: 0;
      }
      .section-grid {
        grid-template-columns: 1fr;
      }
      @media (min-width: 1200px) {
        .section-grid {
          grid-template-columns: 1fr 1fr;
        }
      }
      @media (max-width: 900px) {
        .hero {
          flex-direction: column;
          align-items: stretch;
        }
        .hero-kpis {
          grid-template-columns: 1fr;
        }
        .language-box {
          justify-content: flex-start;
        }
        .layout {
          grid-template-columns: 1fr;
        }
        .sticky-panel {
          position: static;
        }
        .panel-scroller {
          max-height: none;
          overflow: visible;
          padding-right: 0;
        }
        .toolbar {
          grid-template-columns: 1fr;
        }
        body {
          padding: 16px;
        }
        .panel {
          padding: 14px;
        }
        .card {
          padding: 14px;
        }
        .title {
          font-size: 18px;
        }
        .detail-line {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="hero">
        <div class="hero-copy">
          <div class="tagline" id="heroTagline">Retail Market Desk</div>
          <h1 id="heroTitle">US Market Newsboard</h1>
          <p id="heroSubtitle">Built around what retail traders usually watch first: Fed and macro signals, Trump, China, megacap U.S. stocks, earnings and movers, Jensen Huang, Elon Musk, and war or oil catalysts.</p>
        </div>
        <div class="hero-side">
          <div class="language-box">
            <label for="languageSelect" id="languageLabel">Language</label>
            <select id="languageSelect">
              <option value="zh-CN">简体中文</option>
              <option value="en">English</option>
              <option value="zh-TW">繁體中文</option>
              <option value="ja">日本語</option>
              <option value="ko">한국어</option>
              <option value="es">Español</option>
              <option value="fr">Français</option>
            </select>
          </div>
          <div class="hero-kpis">
            <div class="kpi">
              <div class="kpi-label" id="snapshotLabel">Snapshot</div>
              <div class="kpi-value" id="snapshotTime">--</div>
            </div>
            <div class="kpi">
              <div class="kpi-label" id="priorityLabel">Priority</div>
              <div class="kpi-value" id="priorityCount">--</div>
            </div>
            <div class="kpi">
              <div class="kpi-label" id="eventsLabel">Events</div>
              <div class="kpi-value" id="eventsCount">--</div>
            </div>
          </div>
        </div>
      </div>
      <div class="sync-note">
        <div id="syncNote">Waiting for synchronized snapshot...</div>
        <div class="legend">
          <span class="badge badge-bull" id="legendBull">bullish</span>
          <span class="badge badge-bear" id="legendBear">bearish</span>
          <span class="badge badge-watch" id="legendWatch">watch</span>
        </div>
      </div>
      <form id="searchForm" class="toolbar">
        <input id="queryInput" type="text" placeholder="Search headline, summary, source, keyword" />
        <select id="categorySelect">
          <option value="">All categories</option>
          <option value="world">world</option>
          <option value="business">business</option>
          <option value="markets">markets</option>
          <option value="macro">macro</option>
          <option value="policy">policy</option>
          <option value="regulation">regulation</option>
        </select>
        <select id="regionSelect">
          <option value="">All regions</option>
          <option value="global">global</option>
          <option value="us">us</option>
          <option value="china">china</option>
          <option value="europe">europe</option>
          <option value="middle-east">middle-east</option>
        </select>
        <input id="fromDate" type="date" />
        <input id="toDate" type="date" />
        <button type="submit" id="searchBtn">Search</button>
        <button type="button" id="liveBtn" class="alt">Live</button>
      </form>
      <div class="layout">
        <section class="panel">
          <div class="stream-head">
            <div>
              <h2 id="mainStreamTitle">Main Stream</h2>
              <p class="panel-note" id="mainStreamNote">Latest flow first, with direction, impact, targets, and fast source scan.</p>
            </div>
          </div>
          <div class="pager">
            <button type="button" id="prevBtn">Prev</button>
            <span id="pageLabel">Live mode</span>
            <button type="button" id="nextBtn">Next</button>
          </div>
          <div id="stream" class="stream panel-scroller"></div>
        </section>
        <aside class="panel sticky-panel">
          <h2 id="nowMovingTitle">Now Moving</h2>
          <p class="panel-note" id="nowMovingNote">Split by macro, stocks, and geopolitics so you can scan faster.</p>
          <div id="priorityPanel" class="subgrid panel-scroller"></div>
        </aside>
        <aside class="panel sticky-panel">
          <h2 id="traderFocusTitle">Trader Focus</h2>
          <p class="panel-note" id="traderFocusNote">Fixed modules for fast scanning, sector rotation, event awareness, and headline-specific watchlists.</p>
          <div class="subgrid panel-scroller">
            <div class="section-card">
              <h3 id="prepostTitle">盘前盘后与市场异动</h3>
              <div id="moversPanel" class="compact-list"></div>
            </div>
            <div id="sectionsPanel" class="section-grid"></div>
            <div class="section-card">
              <h3 id="eventsPanelTitle">Upcoming Events</h3>
              <div id="eventsPanel" class="compact-list"></div>
            </div>
          </div>
        </aside>
      </div>
    </div>
    <script>
      const streamEl = document.getElementById("stream");
      const priorityPanel = document.getElementById("priorityPanel");
      const sectionsPanel = document.getElementById("sectionsPanel");
      const eventsPanel = document.getElementById("eventsPanel");
      const moversPanel = document.getElementById("moversPanel");
      const snapshotTime = document.getElementById("snapshotTime");
      const priorityCount = document.getElementById("priorityCount");
      const eventsCount = document.getElementById("eventsCount");
      const syncNote = document.getElementById("syncNote");
      const formEl = document.getElementById("searchForm");
      const queryInput = document.getElementById("queryInput");
      const categorySelect = document.getElementById("categorySelect");
      const regionSelect = document.getElementById("regionSelect");
      const fromDate = document.getElementById("fromDate");
      const toDate = document.getElementById("toDate");
      const liveBtn = document.getElementById("liveBtn");
      const prevBtn = document.getElementById("prevBtn");
      const nextBtn = document.getElementById("nextBtn");
      const pageLabel = document.getElementById("pageLabel");
      const languageSelect = document.getElementById("languageSelect");
      let currentLanguage = localStorage.getItem("market_stream_language") || "zh-CN";
      let source;
      let liveMode = true;
      let currentOffset = 0;
      const pageSize = 50;
      let dashboardRefreshTimer = null;
      const ui = {
        "zh-CN": {
          heroTagline: "散户交易台",
          heroTitle: "全球市场消息面板",
          heroSubtitle: "围绕散户最先关注的美联储与宏观、中国与特朗普、美股巨头、财报与异动，以及黄仁勋、马斯克和战争油价信号。",
          languageLabel: "语言",
          snapshotLabel: "快照",
          priorityLabel: "动态",
          eventsLabel: "事件",
          legendBull: "利多",
          legendBear: "利空",
          legendWatch: "观察",
          queryPlaceholder: "搜索标题、摘要、来源、关键词",
          allCategories: "全部分类",
          allRegions: "全部地区",
          searchBtn: "搜索",
          liveBtn: "实时",
          mainStreamTitle: "主消息流",
          mainStreamNote: "按最新排序，优先显示方向、影响等级、影响对象与来源。",
          nowMovingTitle: "正在驱动",
          nowMovingNote: "按宏观、个股、地缘三类拆分，便于快速扫盘。",
          traderFocusTitle: "交易者关注",
          traderFocusNote: "固定模块化观察台，用于盯美联储、债券、贵金属、政策主题和人物线索。",
          prepostTitle: "盘前盘后与市场异动",
          eventsPanelTitle: "即将发生的重要事件",
          prevBtn: "上一页",
          nextBtn: "下一页",
          liveMode: "实时模式",
          historyPage: "历史第 {page} 页 | 当前 {count} 条",
          waitingSync: "等待同步快照...",
          synced: "所有面板已同步至 {time}",
          noMatching: "当前同步快照里暂无匹配消息。",
          noActive: "这一栏当前暂无重点消息。",
          noMovers: "当前暂无 watchlist 盘前盘后快照。",
          impact: "影响",
          targets: "影响对象",
          region: "地区",
          prepostBadge: "盘前/盘后",
          tapeMacro: "宏观驱动",
          tapeStock: "个股异动",
          tapeGeo: "地缘与政策",
          section_market_drivers: "大盘驱动",
          section_bonds_rates: "债券与利率",
          section_dollar_fx: "美元与外汇",
          section_precious_metals: "贵金属",
          section_china_watch: "中国板块",
          section_trump_watch: "特朗普专栏",
          section_jensen_watch: "黄仁勋专栏",
          section_musk_watch: "马斯克专栏",
          section_hot_stocks: "热门股突发",
          section_earnings_guidance: "财报与指引",
          section_policy_regulation_shock: "政策监管冲击",
          section_war_and_oil: "战争与油价",
          categories: {world: "国际", business: "商业", markets: "市场", macro: "宏观", policy: "政策", regulation: "监管"},
          regions: {global: "全球", us: "美国", china: "中国", europe: "欧洲", "middle-east": "中东"},
          directions: {bullish: "利多", bearish: "利空", watch: "观察", mixed: "混合"},
          impacts: {critical: "极高", high: "高", medium: "中", low: "低"},
        },
        "zh-TW": {
          heroTagline: "散戶交易台",
          heroTitle: "全球市場消息面板",
          heroSubtitle: "圍繞散戶最先關注的美聯儲與宏觀、中國與川普、美股巨頭、財報與異動，以及黃仁勳、馬斯克和戰爭油價訊號。",
          languageLabel: "語言",
          snapshotLabel: "快照",
          priorityLabel: "動態",
          eventsLabel: "事件",
          legendBull: "利多",
          legendBear: "利空",
          legendWatch: "觀察",
          queryPlaceholder: "搜尋標題、摘要、來源、關鍵字",
          allCategories: "全部分類",
          allRegions: "全部地區",
          searchBtn: "搜尋",
          liveBtn: "即時",
          mainStreamTitle: "主消息流",
          mainStreamNote: "按最新排序，優先顯示方向、影響等級、影響標的與來源。",
          nowMovingTitle: "正在驅動",
          nowMovingNote: "依宏觀、個股、地緣三類拆分，方便快速掃盤。",
          traderFocusTitle: "交易者關注",
          traderFocusNote: "固定模組化觀察台，用於盯美聯儲、債券、貴金屬、政策主題和人物線索。",
          prepostTitle: "盤前盤後與市場異動",
          eventsPanelTitle: "即將發生的重要事件",
          prevBtn: "上一頁",
          nextBtn: "下一頁",
          liveMode: "即時模式",
          historyPage: "歷史第 {page} 頁 | 目前 {count} 條",
          waitingSync: "等待同步快照...",
          synced: "所有面板已同步至 {time}",
          noMatching: "目前同步快照中暫無符合消息。",
          noActive: "此欄目前暫無重點消息。",
          noMovers: "目前暫無 watchlist 盤前盤後快照。",
          impact: "影響",
          targets: "影響標的",
          region: "地區",
          prepostBadge: "盤前/盤後",
          tapeMacro: "宏觀驅動",
          tapeStock: "個股異動",
          tapeGeo: "地緣與政策",
          section_market_drivers: "大盤驅動",
          section_bonds_rates: "債券與利率",
          section_dollar_fx: "美元與外匯",
          section_precious_metals: "貴金屬",
          section_china_watch: "中國板塊",
          section_trump_watch: "川普專欄",
          section_jensen_watch: "黃仁勳專欄",
          section_musk_watch: "馬斯克專欄",
          section_hot_stocks: "熱門股突發",
          section_earnings_guidance: "財報與指引",
          section_policy_regulation_shock: "政策監管衝擊",
          section_war_and_oil: "戰爭與油價",
          categories: {world: "國際", business: "商業", markets: "市場", macro: "宏觀", policy: "政策", regulation: "監管"},
          regions: {global: "全球", us: "美國", china: "中國", europe: "歐洲", "middle-east": "中東"},
          directions: {bullish: "利多", bearish: "利空", watch: "觀察", mixed: "混合"},
          impacts: {critical: "極高", high: "高", medium: "中", low: "低"},
        },
        "en": {
          heroTagline: "Retail Market Desk",
          heroTitle: "Global Market Newsboard",
          heroSubtitle: "Built around what retail traders usually watch first: Fed and macro signals, Trump, China, megacap U.S. stocks, earnings and movers, Jensen Huang, Elon Musk, and war or oil catalysts.",
          languageLabel: "Language",
          snapshotLabel: "Snapshot",
          priorityLabel: "Moving",
          eventsLabel: "Events",
          legendBull: "Bullish",
          legendBear: "Bearish",
          legendWatch: "Watch",
          queryPlaceholder: "Search headline, summary, source, keyword",
          allCategories: "All categories",
          allRegions: "All regions",
          searchBtn: "Search",
          liveBtn: "Live",
          mainStreamTitle: "Main Stream",
          mainStreamNote: "Latest first, with direction, impact, targets, and source context.",
          nowMovingTitle: "Now Moving",
          nowMovingNote: "Split into macro, stocks, and geopolitics so it is faster to scan.",
          traderFocusTitle: "Trader Focus",
          traderFocusNote: "Fixed watch modules for Fed, bonds, precious metals, policy themes, and person-specific headlines.",
          prepostTitle: "Pre/Post-Market and Movers",
          eventsPanelTitle: "Upcoming Events",
          prevBtn: "Prev",
          nextBtn: "Next",
          liveMode: "Live mode",
          historyPage: "History page {page} | showing {count} items",
          waitingSync: "Waiting for synchronized snapshot...",
          synced: "All panels synced to {time}",
          noMatching: "No matching items in the current synchronized snapshot.",
          noActive: "No active items in this bucket right now.",
          noMovers: "No watchlist mover snapshot right now.",
          impact: "Impact",
          targets: "Targets",
          region: "Region",
          prepostBadge: "Pre/Post",
          tapeMacro: "Macro Now",
          tapeStock: "Stock Now",
          tapeGeo: "Geopolitics Now",
          section_market_drivers: "Market Drivers",
          section_bonds_rates: "Bonds & Rates",
          section_dollar_fx: "Dollar & FX",
          section_precious_metals: "Precious Metals",
          section_china_watch: "China Watch",
          section_trump_watch: "Trump Watch",
          section_jensen_watch: "Jensen Huang",
          section_musk_watch: "Elon Musk",
          section_hot_stocks: "Hot Stocks",
          section_earnings_guidance: "Earnings & Guidance",
          section_policy_regulation_shock: "Policy & Regulation",
          section_war_and_oil: "War & Oil",
          categories: {world: "World", business: "Business", markets: "Markets", macro: "Macro", policy: "Policy", regulation: "Regulation"},
          regions: {global: "Global", us: "US", china: "China", europe: "Europe", "middle-east": "Middle East"},
          directions: {bullish: "Bullish", bearish: "Bearish", watch: "Watch", mixed: "Mixed"},
          impacts: {critical: "Critical", high: "High", medium: "Medium", low: "Low"},
        },
        "ja": {
          heroTagline: "個人投資家デスク",
          heroTitle: "グローバル市場ニュースボード",
          heroSubtitle: "FRBとマクロ、中国とトランプ、米国メガキャップ、決算と値動き、ジェンスン・フアン、イーロン・マスク、戦争と原油材料を優先表示します。",
          languageLabel: "言語",
          snapshotLabel: "スナップショット",
          priorityLabel: "注目",
          eventsLabel: "イベント",
          legendBull: "強気",
          legendBear: "弱気",
          legendWatch: "監視",
          queryPlaceholder: "見出し、要約、ソース、キーワードを検索",
          allCategories: "すべてのカテゴリ",
          allRegions: "すべての地域",
          searchBtn: "検索",
          liveBtn: "ライブ",
          mainStreamTitle: "メインストリーム",
          mainStreamNote: "最新順で、方向、影響度、対象、ソースを先に表示します。",
          nowMovingTitle: "Now Moving",
          nowMovingNote: "マクロ、個別株、地政学に分けて素早く確認できます。",
          traderFocusTitle: "トレーダー注目",
          traderFocusNote: "FRB、債券、貴金属、政策テーマ、人物テーマを固定モジュールで監視します。",
          prepostTitle: "プレ・アフターと市場異動",
          eventsPanelTitle: "今後の重要イベント",
          prevBtn: "前へ",
          nextBtn: "次へ",
          liveMode: "ライブモード",
          historyPage: "履歴ページ {page} | {count} 件表示",
          waitingSync: "同期スナップショットを待機中...",
          synced: "全パネルを {time} に同期しました",
          noMatching: "現在の同期スナップショットに一致する項目はありません。",
          noActive: "この枠には現在注目項目がありません。",
          noMovers: "ウォッチリストのプレ・アフタースナップショットは現在ありません。",
          impact: "影響",
          targets: "対象",
          region: "地域",
          prepostBadge: "プレ/アフター",
          tapeMacro: "マクロ",
          tapeStock: "個別株",
          tapeGeo: "地政学",
          section_market_drivers: "市場ドライバー",
          section_bonds_rates: "債券と金利",
          section_dollar_fx: "ドルと為替",
          section_precious_metals: "貴金属",
          section_china_watch: "中国ウォッチ",
          section_trump_watch: "トランプ欄",
          section_jensen_watch: "ジェンスン・フアン",
          section_musk_watch: "イーロン・マスク",
          section_hot_stocks: "人気株速報",
          section_earnings_guidance: "決算とガイダンス",
          section_policy_regulation_shock: "政策・規制ショック",
          section_war_and_oil: "戦争と原油",
          categories: {world: "国際", business: "ビジネス", markets: "市場", macro: "マクロ", policy: "政策", regulation: "規制"},
          regions: {global: "グローバル", us: "米国", china: "中国", europe: "欧州", "middle-east": "中東"},
          directions: {bullish: "強気", bearish: "弱気", watch: "監視", mixed: "混在"},
          impacts: {critical: "非常に高い", high: "高い", medium: "中程度", low: "低い"},
        },
        "ko": {
          heroTagline: "개인투자자 데스크",
          heroTitle: "글로벌 마켓 뉴스보드",
          heroSubtitle: "연준과 거시 지표, 중국과 트럼프, 미국 메가캡, 실적과 급등락, 젠슨 황, 일론 머스크, 전쟁·유가 재료를 우선 보여줍니다.",
          languageLabel: "언어",
          snapshotLabel: "스냅샷",
          priorityLabel: "동향",
          eventsLabel: "이벤트",
          legendBull: "강세",
          legendBear: "약세",
          legendWatch: "관찰",
          queryPlaceholder: "제목, 요약, 출처, 키워드 검색",
          allCategories: "전체 카테고리",
          allRegions: "전체 지역",
          searchBtn: "검색",
          liveBtn: "실시간",
          mainStreamTitle: "메인 스트림",
          mainStreamNote: "최신순으로, 방향·영향도·대상·출처를 먼저 보여줍니다.",
          nowMovingTitle: "Now Moving",
          nowMovingNote: "거시, 종목, 지정학으로 나눠 더 빠르게 스캔할 수 있습니다.",
          traderFocusTitle: "트레이더 포커스",
          traderFocusNote: "연준, 채권, 귀금속, 정책 테마와 인물 헤드라인을 고정 모듈로 봅니다.",
          prepostTitle: "프리/애프터마켓과 시장 급변",
          eventsPanelTitle: "예정된 중요 이벤트",
          prevBtn: "이전",
          nextBtn: "다음",
          liveMode: "실시간 모드",
          historyPage: "히스토리 {page}페이지 | {count}개 표시",
          waitingSync: "동기화된 스냅샷을 기다리는 중...",
          synced: "모든 패널이 {time} 기준으로 동기화됨",
          noMatching: "현재 동기화 스냅샷에 맞는 항목이 없습니다.",
          noActive: "현재 이 버킷에는 핵심 항목이 없습니다.",
          noMovers: "현재 워치리스트 프리/애프터 스냅샷이 없습니다.",
          impact: "영향",
          targets: "대상",
          region: "지역",
          prepostBadge: "프리/애프터",
          tapeMacro: "거시",
          tapeStock: "종목",
          tapeGeo: "지정학",
          section_market_drivers: "시장 동인",
          section_bonds_rates: "채권·금리",
          section_dollar_fx: "달러·외환",
          section_precious_metals: "귀금속",
          section_china_watch: "중국 섹션",
          section_trump_watch: "트럼프 섹션",
          section_jensen_watch: "젠슨 황",
          section_musk_watch: "일론 머스크",
          section_hot_stocks: "인기 종목",
          section_earnings_guidance: "실적과 가이던스",
          section_policy_regulation_shock: "정책·규제 충격",
          section_war_and_oil: "전쟁과 유가",
          categories: {world: "국제", business: "비즈니스", markets: "시장", macro: "거시", policy: "정책", regulation: "규제"},
          regions: {global: "글로벌", us: "미국", china: "중국", europe: "유럽", "middle-east": "중동"},
          directions: {bullish: "강세", bearish: "약세", watch: "관찰", mixed: "혼조"},
          impacts: {critical: "매우 높음", high: "높음", medium: "중간", low: "낮음"},
        },
        "es": {
          heroTagline: "Mesa del Inversor Minorista",
          heroTitle: "Global Market Newsboard",
          heroSubtitle: "Pensado para lo que un trader minorista suele mirar primero: Fed y macro, Trump y China, megacaps de EE. UU., resultados y movimientos, Jensen Huang, Elon Musk, y catalizadores de guerra o petróleo.",
          languageLabel: "Idioma",
          snapshotLabel: "Instantánea",
          priorityLabel: "Movimiento",
          eventsLabel: "Eventos",
          legendBull: "Alcista",
          legendBear: "Bajista",
          legendWatch: "Vigilar",
          queryPlaceholder: "Buscar titular, resumen, fuente o palabra clave",
          allCategories: "Todas las categorías",
          allRegions: "Todas las regiones",
          searchBtn: "Buscar",
          liveBtn: "En vivo",
          mainStreamTitle: "Flujo Principal",
          mainStreamNote: "Lo más reciente primero, con dirección, impacto, objetivos y contexto de fuente.",
          nowMovingTitle: "Now Moving",
          nowMovingNote: "Separado por macro, acciones y geopolítica para escanear más rápido.",
          traderFocusTitle: "Enfoque del Trader",
          traderFocusNote: "Módulos fijos para Fed, bonos, metales preciosos, temas regulatorios y titulares por persona.",
          prepostTitle: "Pre/Post-Market y Movers",
          eventsPanelTitle: "Próximos Eventos",
          prevBtn: "Anterior",
          nextBtn: "Siguiente",
          liveMode: "Modo en vivo",
          historyPage: "Página histórica {page} | {count} elementos",
          waitingSync: "Esperando instantánea sincronizada...",
          synced: "Todos los paneles sincronizados a las {time}",
          noMatching: "No hay elementos coincidentes en la instantánea actual.",
          noActive: "No hay elementos activos en este bloque ahora.",
          noMovers: "No hay instantánea de movers del watchlist por ahora.",
          impact: "Impacto",
          targets: "Objetivos",
          region: "Región",
          prepostBadge: "Pre/Post",
          tapeMacro: "Macro",
          tapeStock: "Acciones",
          tapeGeo: "Geopolítica",
          section_market_drivers: "Impulsores del Mercado",
          section_bonds_rates: "Bonos y Tasas",
          section_dollar_fx: "Dólar y FX",
          section_precious_metals: "Metales Preciosos",
          section_china_watch: "China",
          section_trump_watch: "Trump",
          section_jensen_watch: "Jensen Huang",
          section_musk_watch: "Elon Musk",
          section_hot_stocks: "Acciones Calientes",
          section_earnings_guidance: "Resultados y Guía",
          section_policy_regulation_shock: "Política y Regulación",
          section_war_and_oil: "Guerra y Petróleo",
          categories: {world: "Mundo", business: "Negocios", markets: "Mercados", macro: "Macro", policy: "Política", regulation: "Regulación"},
          regions: {global: "Global", us: "EE. UU.", china: "China", europe: "Europa", "middle-east": "Medio Oriente"},
          directions: {bullish: "Alcista", bearish: "Bajista", watch: "Vigilar", mixed: "Mixto"},
          impacts: {critical: "Crítico", high: "Alto", medium: "Medio", low: "Bajo"},
        },
        "fr": {
          heroTagline: "Desk Trader Particulier",
          heroTitle: "Global Market Newsboard",
          heroSubtitle: "Conçu autour de ce qu’un trader particulier regarde d’abord : Fed et macro, Trump et Chine, mégacaps américaines, résultats et mouvements, Jensen Huang, Elon Musk, ainsi que guerre et pétrole.",
          languageLabel: "Langue",
          snapshotLabel: "Instantané",
          priorityLabel: "Mouvement",
          eventsLabel: "Événements",
          legendBull: "Haussier",
          legendBear: "Baissier",
          legendWatch: "Surveiller",
          queryPlaceholder: "Rechercher titre, résumé, source ou mot-clé",
          allCategories: "Toutes les catégories",
          allRegions: "Toutes les régions",
          searchBtn: "Rechercher",
          liveBtn: "Live",
          mainStreamTitle: "Flux Principal",
          mainStreamNote: "Le plus récent d’abord, avec direction, impact, cibles et source.",
          nowMovingTitle: "Now Moving",
          nowMovingNote: "Découpé en macro, actions et géopolitique pour une lecture plus rapide.",
          traderFocusTitle: "Focus Trader",
          traderFocusNote: "Modules fixes pour la Fed, les obligations, les métaux précieux, les thèmes politiques et les personnalités.",
          prepostTitle: "Pré/Post-Marché et Movers",
          eventsPanelTitle: "Événements à Venir",
          prevBtn: "Précédent",
          nextBtn: "Suivant",
          liveMode: "Mode live",
          historyPage: "Page historique {page} | {count} éléments",
          waitingSync: "En attente d’un instantané synchronisé...",
          synced: "Tous les panneaux sont synchronisés à {time}",
          noMatching: "Aucun élément correspondant dans l’instantané actuel.",
          noActive: "Aucun élément actif dans cette section pour le moment.",
          noMovers: "Aucun snapshot pre/post-market du watchlist pour le moment.",
          impact: "Impact",
          targets: "Cibles",
          region: "Région",
          prepostBadge: "Pré/Post",
          tapeMacro: "Macro",
          tapeStock: "Actions",
          tapeGeo: "Géopolitique",
          section_market_drivers: "Moteurs du Marché",
          section_bonds_rates: "Obligations et Taux",
          section_dollar_fx: "Dollar et FX",
          section_precious_metals: "Métaux Précieux",
          section_china_watch: "Chine",
          section_trump_watch: "Trump",
          section_jensen_watch: "Jensen Huang",
          section_musk_watch: "Elon Musk",
          section_hot_stocks: "Actions Chaudes",
          section_earnings_guidance: "Résultats et Guidance",
          section_policy_regulation_shock: "Politique et Régulation",
          section_war_and_oil: "Guerre et Pétrole",
          categories: {world: "Monde", business: "Business", markets: "Marchés", macro: "Macro", policy: "Politique", regulation: "Régulation"},
          regions: {global: "Global", us: "États-Unis", china: "Chine", europe: "Europe", "middle-east": "Moyen-Orient"},
          directions: {bullish: "Haussier", bearish: "Baissier", watch: "Surveiller", mixed: "Mixte"},
          impacts: {critical: "Critique", high: "Élevé", medium: "Moyen", low: "Faible"},
        },
      };

      function t(key, replacements = {}) {
        const langPack = ui[currentLanguage] || ui["en"];
        let value = langPack[key] ?? ui["en"][key] ?? key;
        for (const [name, replacement] of Object.entries(replacements)) {
          value = value.replace(`{${name}}`, replacement);
        }
        return value;
      }

      function translateCategory(value) {
        const langPack = ui[currentLanguage] || ui["en"];
        return langPack.categories?.[value] || value;
      }

      function translateRegion(value) {
        const langPack = ui[currentLanguage] || ui["en"];
        return langPack.regions?.[value] || value;
      }

      function badgeClass(value) {
        if (value === "bullish") return "badge badge-bull";
        if (value === "bearish") return "badge badge-bear";
        if (value === "watch" || value === "mixed") return "badge badge-watch";
        return "badge badge-neutral";
      }

      function labelText(value) {
        const clean = String(value || "").replaceAll("_", " ");
        const normalized = String(value || "");
        const langPack = ui[currentLanguage] || ui["en"];
        return langPack.directions?.[normalized] || langPack.impacts?.[normalized] || clean;
      }

      function applyTranslations() {
        document.documentElement.lang = currentLanguage;
        document.title = t("heroTitle");
        document.getElementById("heroTagline").textContent = t("heroTagline");
        document.getElementById("heroTitle").textContent = t("heroTitle");
        document.getElementById("heroSubtitle").textContent = t("heroSubtitle");
        document.getElementById("languageLabel").textContent = t("languageLabel");
        document.getElementById("snapshotLabel").textContent = t("snapshotLabel");
        document.getElementById("priorityLabel").textContent = t("priorityLabel");
        document.getElementById("eventsLabel").textContent = t("eventsLabel");
        document.getElementById("legendBull").textContent = t("legendBull");
        document.getElementById("legendBear").textContent = t("legendBear");
        document.getElementById("legendWatch").textContent = t("legendWatch");
        queryInput.placeholder = t("queryPlaceholder");
        categorySelect.options[0].text = t("allCategories");
        categorySelect.options[1].text = translateCategory("world");
        categorySelect.options[2].text = translateCategory("business");
        categorySelect.options[3].text = translateCategory("markets");
        categorySelect.options[4].text = translateCategory("macro");
        categorySelect.options[5].text = translateCategory("policy");
        categorySelect.options[6].text = translateCategory("regulation");
        regionSelect.options[0].text = t("allRegions");
        regionSelect.options[1].text = translateRegion("global");
        regionSelect.options[2].text = translateRegion("us");
        regionSelect.options[3].text = translateRegion("china");
        regionSelect.options[4].text = translateRegion("europe");
        regionSelect.options[5].text = translateRegion("middle-east");
        document.getElementById("searchBtn").textContent = t("searchBtn");
        liveBtn.textContent = t("liveBtn");
        document.getElementById("mainStreamTitle").textContent = t("mainStreamTitle");
        document.getElementById("mainStreamNote").textContent = t("mainStreamNote");
        document.getElementById("nowMovingTitle").textContent = t("nowMovingTitle");
        document.getElementById("nowMovingNote").textContent = t("nowMovingNote");
        document.getElementById("traderFocusTitle").textContent = t("traderFocusTitle");
        document.getElementById("traderFocusNote").textContent = t("traderFocusNote");
        document.getElementById("prepostTitle").textContent = t("prepostTitle");
        document.getElementById("eventsPanelTitle").textContent = t("eventsPanelTitle");
        prevBtn.textContent = t("prevBtn");
        nextBtn.textContent = t("nextBtn");
        if (liveMode) {
          pageLabel.textContent = t("liveMode");
        }
      }

      function card(item) {
        const articleUrl = item.url || item.source_homepage;
        const classification = item.classification || {};
        const targets = (classification.affected_targets || []).join(", ") || "SPY";
        const lagMinutes = Math.max(0, Math.round((new Date(item.fetched_at) - new Date(item.published_at)) / 60000));
        const lagText = lagMinutes < 60 ? `${lagMinutes}m` : `${Math.floor(lagMinutes / 60)}h ${lagMinutes % 60}m`;
        return `
          <article class="card">
            <div class="meta-row">
              <div class="meta-left">
                <span class="badge badge-neutral">${item.source_name}</span>
                <span class="badge badge-neutral">${translateCategory(item.source_category)}</span>
                <span class="${badgeClass(classification.impact_direction)}">${labelText(classification.impact_direction)}</span>
                <span class="badge badge-neutral">lag ${lagText}</span>
              </div>
              <div class="meta-right">
                <div class="meta">${new Date(item.published_at).toLocaleString()}</div>
              </div>
            </div>
            <div class="title"><a href="${articleUrl}" target="_blank" rel="noreferrer">${item.title}</a></div>
            <div class="detail-line">
              <div class="detail-pill">
                <div class="detail-label">${t("impact")}</div>
                <div class="detail-value">${labelText(classification.impact_level) || "low"}</div>
              </div>
              <div class="detail-pill">
                <div class="detail-label">${t("targets")}</div>
                <div class="detail-value">${targets}</div>
              </div>
              <div class="detail-pill">
                <div class="detail-label">${t("region")}</div>
                <div class="detail-value">${translateRegion(item.source_region)}</div>
              </div>
            </div>
            <div class="summary">${item.summary || ""}</div>
            <div class="line">${item.alert_text}</div>
          </article>
        `;
      }

      function compactPriority(item) {
        const articleUrl = item.url || item.source_homepage;
        const lagMinutes = Math.max(0, Math.round((new Date(item.fetched_at) - new Date(item.published_at)) / 60000));
        const lagText = lagMinutes < 60 ? `${lagMinutes}m` : `${Math.floor(lagMinutes / 60)}h ${lagMinutes % 60}m`;
        return `
          <article class="compact-card">
            <div class="meta-row">
              <div class="meta-left">
                <span class="badge badge-neutral">${labelText(item.classification?.primary_label || item.source_category)}</span>
                <span class="${badgeClass(item.classification?.impact_direction)}">${labelText(item.classification?.impact_direction || "watch")}</span>
                <span class="badge badge-neutral">lag ${lagText}</span>
              </div>
              <div class="meta">${new Date(item.published_at).toLocaleTimeString()}</div>
            </div>
            <div class="compact-title"><a href="${articleUrl}" target="_blank" rel="noreferrer">${item.title}</a></div>
            <div class="compact-meta">${item.source_name} | ${t("impact")} ${labelText(item.classification?.impact_level || "low")} | ${(item.classification?.affected_targets || []).join(", ") || "SPY"}</div>
          </article>
        `;
      }

      function tapeSection(title, items) {
        return `
          <section class="section-card">
            <h3>${title}</h3>
            <div class="compact-list">
              ${items.length ? items.map(compactPriority).join("") : `<article class="compact-card"><div class="compact-meta">${t("noActive")}</div></article>`}
            </div>
          </section>
        `;
      }

      function compactEvent(item) {
        return `
          <article class="compact-card">
            <div class="compact-title"><a href="${item.source_url}" target="_blank" rel="noreferrer">${item.title}</a></div>
            <div class="compact-meta">${item.source_name} | ${item.category}</div>
            <div class="line">${new Date(item.event_time).toLocaleString()}\n${item.note || ""}</div>
          </article>
        `;
      }

      function compactMover(item) {
        if (item.title) {
          const articleUrl = item.url || item.source_homepage;
          return `
            <article class="compact-card">
              <div class="meta-row">
                <div class="meta-left">
                  <span class="${badgeClass(item.classification?.impact_direction)}">${labelText(item.classification?.impact_direction || "watch")}</span>
                </div>
                <div class="meta">${new Date(item.published_at).toLocaleTimeString()}</div>
              </div>
              <div class="compact-title"><a href="${articleUrl}" target="_blank" rel="noreferrer">${item.title}</a></div>
              <div class="compact-meta">${item.source_name}</div>
            </article>
          `;
        }
        return `
          <article class="compact-card">
            <div class="meta-row">
              <div class="meta-left">
                <span class="badge badge-neutral">${t("prepostBadge")}</span>
              </div>
            </div>
            <div class="compact-title"><a href="${item.source_url}" target="_blank" rel="noreferrer">${item.symbol}</a></div>
            <div class="compact-meta">${item.source_name}</div>
            <div class="line">Last: ${item.last || "--"}\nChange: ${item.change || "--"} (${item.change_pct || "--"})</div>
          </article>
        `;
      }

      function sectionBlock(title, items) {
        return `
          <section class="section-card">
            <h3>${title}</h3>
            <div class="compact-list">
              ${items.length ? items.map((item) => {
                const articleUrl = item.url || item.source_homepage;
                const classification = item.classification || {};
                return `
                  <article class="compact-card">
                    <div class="badge-row">
                      <span class="${badgeClass(classification.impact_direction)}">${labelText(classification.impact_direction || "watch")}</span>
                      <span class="badge badge-neutral">${labelText(classification.impact_level || "low")}</span>
                    </div>
                    <div class="compact-title"><a href="${articleUrl}" target="_blank" rel="noreferrer">${item.title}</a></div>
                    <div class="compact-meta">${classification.primary_label || "unclassified"} | ${(classification.affected_targets || []).join(", ") || "SPY"}</div>
                  </article>
                `;
              }).join("") : `<article class="compact-card"><div class="compact-meta">${t("noMatching")}</div></article>`}
            </div>
          </section>
        `;
      }

      async function loadInitial() {
        const response = await fetch(`/api/items?limit=${pageSize}`);
        const data = await response.json();
        streamEl.innerHTML = data.items.map(card).join("");
        pageLabel.textContent = t("liveMode");
      }

      async function loadDashboardSnapshot() {
        const response = await fetch("/api/dashboard");
        const data = await response.json();
        if (liveMode) {
          streamEl.innerHTML = data.stream.map(card).join("");
        }
        priorityPanel.innerHTML = [
          tapeSection(t("tapeMacro"), data.now_moving?.macro_now || []),
          tapeSection(t("tapeStock"), data.now_moving?.stock_now || []),
          tapeSection(t("tapeGeo"), data.now_moving?.geopolitics_now || []),
        ].join("");
        eventsPanel.innerHTML = data.events.map(compactEvent).join("");
        sectionsPanel.innerHTML = [
          sectionBlock(t("section_market_drivers"), data.sections.market_drivers || []),
          sectionBlock(t("section_bonds_rates"), data.sections.bonds_rates || []),
          sectionBlock(t("section_dollar_fx"), data.sections.dollar_fx || []),
          sectionBlock(t("section_precious_metals"), data.sections.precious_metals || []),
          sectionBlock(t("section_china_watch"), data.sections.china_watch || []),
          sectionBlock(t("section_trump_watch"), data.sections.trump_watch || []),
          sectionBlock(t("section_jensen_watch"), data.sections.jensen_watch || []),
          sectionBlock(t("section_musk_watch"), data.sections.musk_watch || []),
          sectionBlock(t("section_hot_stocks"), data.sections.hot_stocks || []),
          sectionBlock(t("section_earnings_guidance"), data.sections.earnings_guidance || []),
          sectionBlock(t("section_policy_regulation_shock"), data.sections.policy_regulation_shock || []),
          sectionBlock(t("section_war_and_oil"), data.sections.war_and_oil || []),
        ].join("");
        moversPanel.innerHTML = (data.prepost_movers || []).map(compactMover).join("") || `<div class="compact-meta">${t("noMovers")}</div>`;
        snapshotTime.textContent = new Date(data.generated_at).toLocaleTimeString();
        priorityCount.textContent = String(
          (data.now_moving?.macro_now || []).length +
          (data.now_moving?.stock_now || []).length +
          (data.now_moving?.geopolitics_now || []).length
        );
        eventsCount.textContent = String(data.events.length);
        syncNote.textContent = t("synced", {time: new Date(data.generated_at).toLocaleString()});
      }

      function scheduleDashboardRefresh(delay = 300) {
        if (dashboardRefreshTimer) {
          clearTimeout(dashboardRefreshTimer);
        }
        dashboardRefreshTimer = setTimeout(() => {
          loadDashboardSnapshot();
          dashboardRefreshTimer = null;
        }, delay);
      }

      function closeStream() {
        if (source) {
          source.close();
          source = null;
        }
      }

      async function fetchHistory(offset = 0) {
        const params = new URLSearchParams();
        const q = queryInput.value.trim();
        const sourceCategory = categorySelect.value;
        const sourceRegion = regionSelect.value;
        const startAt = fromDate.value;
        const endAt = toDate.value;
        params.set("limit", String(pageSize));
        params.set("offset", String(offset));
        if (q) params.set("q", q);
        if (sourceCategory) params.set("source_category", sourceCategory);
        if (sourceRegion) params.set("source_region", sourceRegion);
        if (startAt) params.set("start_date", startAt);
        if (endAt) params.set("end_date", endAt);
        const endpoint = `/api/search?${params}`;
        const response = await fetch(endpoint);
        const data = await response.json();
        streamEl.innerHTML = data.items.map(card).join("");
        currentOffset = offset;
        const pageNumber = Math.floor(currentOffset / pageSize) + 1;
        pageLabel.textContent = t("historyPage", {page: pageNumber, count: data.count});
        prevBtn.disabled = currentOffset === 0;
        nextBtn.disabled = data.count < pageSize;
      }

      async function runSearch(event) {
        event.preventDefault();
        liveMode = false;
        closeStream();
        await fetchHistory(0);
      }

      function attachStream() {
        source = new EventSource("/stream");
        source.addEventListener("item", (event) => {
          const item = JSON.parse(event.data);
          streamEl.insertAdjacentHTML("afterbegin", card(item));
          while (streamEl.children.length > 80) {
            streamEl.removeChild(streamEl.lastElementChild);
          }
          scheduleDashboardRefresh(150);
        });
      }

      function resetLiveMode() {
        closeStream();
        liveMode = true;
        currentOffset = 0;
        queryInput.value = "";
        categorySelect.value = "";
        regionSelect.value = "";
        fromDate.value = "";
        toDate.value = "";
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        loadDashboardSnapshot().then(attachStream);
      }

      async function previousPage() {
        if (liveMode || currentOffset === 0) return;
        await fetchHistory(Math.max(0, currentOffset - pageSize));
      }

      async function nextPage() {
        if (liveMode) return;
        await fetchHistory(currentOffset + pageSize);
      }

      formEl.addEventListener("submit", runSearch);
      liveBtn.addEventListener("click", resetLiveMode);
      prevBtn.addEventListener("click", previousPage);
      nextBtn.addEventListener("click", nextPage);
      languageSelect.value = currentLanguage;
      languageSelect.addEventListener("change", async (event) => {
        currentLanguage = event.target.value;
        localStorage.setItem("market_stream_language", currentLanguage);
        applyTranslations();
        if (liveMode) {
          await loadDashboardSnapshot();
        } else {
          await fetchHistory(currentOffset);
        }
      });
      prevBtn.disabled = true;
      nextBtn.disabled = true;
      applyTranslations();
      loadDashboardSnapshot().then(attachStream);
      setInterval(loadDashboardSnapshot, 60000);
    </script>
  </body>
</html>
"""


@app.get("/api/items")
async def get_items(
    limit: int = 50,
    offset: int = 0,
    source_category: str | None = None,
    source_region: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, object]:
    items = [
        item.as_dict()
        for item in service.history_items(
            limit=limit,
            offset=offset,
            source_category=source_category,
            source_region=source_region,
            start_at=parse_day_start(start_date),
            end_at=parse_day_end(end_date),
        )
    ]
    return {"count": len(items), "items": items, "errors": service.recent_errors()}


@app.get("/health")
async def health() -> dict[str, object]:
    return service.health_status()


@app.get("/api/priority")
async def priority_items(limit: int = 25) -> dict[str, object]:
    items = service.high_priority_items(limit=limit)
    return {"count": len(items), "items": items}


@app.get("/api/events")
async def upcoming_events() -> dict[str, object]:
    events = [event.as_dict() for event in await service.upcoming_events()]
    return {"count": len(events), "items": events}


@app.get("/api/dashboard")
async def dashboard() -> dict[str, object]:
    recent_items = [item.as_dict() for item in service.recent_items(limit=30)]
    priority_items = service.trader_focus_items(limit=8)
    now_moving = service.now_moving_sections(limit_per_section=3)
    events = [event.as_dict() for event in await service.upcoming_events()]
    retail = await service.retail_snapshot(limit_per_section=5)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stream": recent_items,
        "priority": priority_items,
        "now_moving": now_moving,
        "events": events,
        "sections": retail["sections"],
        "prepost_movers": retail["prepost_movers"],
    }


@app.get("/api/search")
async def search_items(
    q: str = "",
    limit: int = 50,
    offset: int = 0,
    source_category: str | None = None,
    source_region: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, object]:
    start_at = parse_day_start(start_date)
    end_at = parse_day_end(end_date)
    if not q.strip():
        items = [
            item.as_dict()
            for item in service.history_items(
                limit=limit,
                offset=offset,
                source_category=source_category,
                source_region=source_region,
                start_at=start_at,
                end_at=end_at,
            )
        ]
    else:
        items = [
            item.as_dict()
            for item in service.search_items(
                query=q,
                limit=limit,
                offset=offset,
                source_category=source_category,
                source_region=source_region,
                start_at=start_at,
                end_at=end_at,
            )
        ]
    return {
        "count": len(items),
        "query": q,
        "offset": offset,
        "source_category": source_category,
        "source_region": source_region,
        "start_date": start_date,
        "end_date": end_date,
        "items": items,
    }


@app.get("/api/text", response_class=PlainTextResponse)
async def get_text(
    limit: int = 50,
    offset: int = 0,
    q: str = "",
    source_category: str | None = None,
    source_region: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    start_at = parse_day_start(start_date)
    end_at = parse_day_end(end_date)
    if not q.strip():
        items = service.history_items(
            limit=limit,
            offset=offset,
            source_category=source_category,
            source_region=source_region,
            start_at=start_at,
            end_at=end_at,
        )
    else:
        items = service.search_items(
            query=q,
            limit=limit,
            offset=offset,
            source_category=source_category,
            source_region=source_region,
            start_at=start_at,
            end_at=end_at,
        )
    blocks = [item.as_alert_text() for item in items]
    return "\n\n".join(blocks)


@app.get("/stream")
async def stream() -> StreamingResponse:
    return StreamingResponse(service.stream(), media_type="text/event-stream")
