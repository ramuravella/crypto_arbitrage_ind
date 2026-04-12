
const token = localStorage.getItem('aq_token');
const role  = localStorage.getItem('aq_role');
if (!token) { window.location.href = '/login'; }

let ws, state = {opps:[], positions:[], balances:{}, history:[], autoMode:false};
let selectedOpp = null, inrRate = 88.5;
let isAdmin = role === 'admin';
let intervalFilter = 'all';

// Fetch INR rate
fetch('/fx/inr-rate').then(r=>r.json()).then(d=>{ inrRate = d.rate || 88.5; });

// ── WebSocket ──────────────────────────────────────────────────────────────
function setFilter(f) {
  intervalFilter = f;
  ['all','1','4','8'].forEach(function(x) {
    var btn = document.getElementById('f-'+x);
    if (!btn) return;
    btn.style.background = x === f ? 'var(--accent)' : 'transparent';
    btn.style.color = x === f ? '#000' : 'var(--muted)';
    btn.style.fontWeight = x === f ? '700' : '400';
  });
  renderOpps();
}
function connect() {
  const dot = document.getElementById('scan-dot');
  ws = new WebSocket(`ws://${location.host}/ws?token=${token}`);
  ws.onopen = () => { 
    dot.classList.add('scanning');
    // Start position polling when WebSocket connects
    startPositionPolling();
  };
  ws.onclose = (ev) => { 
    dot.classList.remove('scanning'); 
    stopPositionPolling();
    // 4001 = auth failure — redirect to login instead of reconnecting
    if (ev.code === 4001) {
      localStorage.clear();
      window.location.href = '/login';
      return;
    }
    setTimeout(connect, 3000); 
  };
  ws.onerror = () => ws.close();
  ws.onmessage = (ev) => {
    try {
      const d = JSON.parse(ev.data);
      if (d.type === 'update') handleUpdate(d);
      else if (d.type === 'funding_received') handleFundingReceived(d);
    } catch(e) {}
  };
}

let positionPollTimer = null;

function startPositionPolling() {
  // Poll positions every 1 second for real-time P&L updates
  if (positionPollTimer) clearInterval(positionPollTimer);
  
  positionPollTimer = setInterval(() => {
    // ALWAYS poll to verify positions (even when empty),
    // so we know when positions are successfully removed
    
    // Fetch fresh position data
    authFetch('/api/positions')
      .then(r => r.json())
      .then(d => {
        if (d.positions !== undefined) {
          // Update positions and recalculate P&L based on live prices
          state.positions = d.positions;
          
          // Recalculate P&L for each position based on current opportunity prices
          state.positions.forEach(pos => {
            const opp = state.opps.find(o => o.symbol === pos.symbol);
            if (opp) {
              // Calculate unrealized P&L based on live prices
              const qty = parseFloat(pos.qty || 0);
              const shortEntry = parseFloat(pos.short_entry_price || 0);
              const longEntry = parseFloat(pos.long_entry_price || 0);
              const shortPrice = parseFloat(opp.short_price || opp.price || 0);
              const longPrice = parseFloat(opp.long_price || opp.price || 0);
              
              if (qty && shortEntry && longEntry && shortPrice && longPrice) {
                // Unrealized P&L: profit if short went down or long went up
                const unrealized = (shortEntry - shortPrice) * qty + (longPrice - longEntry) * qty;
                pos.unrealised_pnl = unrealized;
                
                // Total P&L = realized (funding - fees) + unrealized
                const realized = parseFloat(pos.cumulative_funding || 0) - (parseFloat(pos.entry_fee_usdt || 0) * 2);
                pos.net_pnl = realized + unrealized;
              }
            }
          });
          
          renderPositions();
        }
      })
      .catch(e => console.debug('[PositionPoll] Error:', e));
  }, 1000);  // Update every second
}

function stopPositionPolling() {
  if (positionPollTimer) {
    clearInterval(positionPollTimer);
    positionPollTimer = null;
  }
}

function handleUpdate(d) {
  state.opps      = d.opportunities || [];
  state.positions = d.positions || [];
  state.balances  = d.balances || {};
  state.history   = d.order_history || [];
  state.autoMode  = d.auto_mode;

  document.getElementById('scan-dot').classList.add('scanning');

  updateBalances();
  renderOpps();
  renderPositions();
  updateModeBadge();
  if (selectedOpp) {
    const fresh = state.opps.find(o => o.symbol === selectedOpp.symbol);
    if (fresh) { selectedOpp = fresh; renderDetail(fresh); }
  }
}

function handleFundingReceived(d) {
  const symbol = d.symbol;
  const payout = d.payout || 0;
  const cumulative = d.cumulative || 0;
  
  // Show toast notification
  toast(`✓ ${symbol}: Funding received +$${payout.toFixed(6)}`, 'success');
  
  // Update position data immediately so renderPositions shows new funding
  const pos = state.positions.find(p => p.symbol === symbol);
  if (pos) {
    pos.cumulative_funding = cumulative;
  }
  
  // Re-render positions first so the card exists in DOM
  renderPositions();
  
  // Find position card and add green tick + glow animation
  const cards = document.querySelectorAll('[data-symbol="'+symbol+'"]');
  if (cards.length > 0) {
    const card = cards[0];
    card.classList.add('funding-received');
    const tick = document.createElement('div');
    tick.className = 'funding-tick';
    tick.innerHTML = '✓';
    card.appendChild(tick);
    setTimeout(() => { tick.remove(); card.classList.remove('funding-received'); }, 3000);
  }
}

function updateBalances() {
  const b = state.balances;
  const el = (id, v, prefix='$') => {
    const e = document.getElementById(id);
    if (!e) return;
    e.textContent = v != null ? prefix + parseFloat(v).toFixed(2) : '—';
    e.classList.toggle('loading', v == null);
  };
  el('bal-dcx', b.coindcx, '₹');
  el('bal-cs', b.coinswitch, '$');
  // Fetch CS futures INR balance — throttled to once per 30s
  const now = Date.now();
  if (!window._lastCSBalFetch || now - window._lastCSBalFetch > 30000) {
    window._lastCSBalFetch = now;
    fetchCSBalance();
  }
}

async function fetchCSBalance() {
  try {
    const r = await authFetch('/api/coinswitch/balance');
    const d = await r.json();
    const el = document.getElementById('bal-cs-inr');
    if (d.futures_inr_balance != null) {
      el.textContent = '₹' + parseFloat(d.futures_inr_balance).toFixed(0);
      el.classList.remove('loading');
    }
  } catch(e) {}
}

// ── Render Opportunities ───────────────────────────────────────────────────
function renderOpps() {
  const list = document.getElementById('opp-list');
  // Filter: only show symbols available on both exchanges
  var filtered = state.opps.filter(o => o.available_on_both);
  filtered = intervalFilter === 'all' ? filtered : filtered.filter(function(o){ return String(o.interval_hours) === intervalFilter; });
  document.getElementById('opp-count').textContent = filtered.length + ' pairs';
  if (!filtered.length) {
    list.innerHTML = '<div style="padding:24px;text-align:center;color:var(--dim);font-size:11px">No opportunities above threshold</div>';
    return;
  }
  list.innerHTML = filtered.map(o => {
    const cls = o.spread_pct >= 1 ? 'high' : o.spread_pct >= 0.3 ? 'mid' : 'low';
    const actionable = o.minutes_to_settlement >= 15 && o.minutes_to_settlement <= 45 && o.stability_count >= 2;
    const sel = selectedOpp?.symbol === o.symbol ? 'selected' : '';
    const stabDots = Array.from({length:3}, (_,i) =>
      `<div class="stab-dot ${i < o.stability_count ? 'filled' : ''}"></div>`).join('');
    const mins = o.minutes_to_settlement;
    const minsStr = mins > 60 ? (mins/60).toFixed(1)+'h' : Math.round(mins)+'m';
    const chg = parseFloat(o.change_24h_pct || 0);
    const chgCls = chg > 0 ? 'style="color:var(--green)"' : chg < 0 ? 'style="color:var(--red)"' : '';
    const chgStr = (chg >= 0 ? '+' : '') + chg.toFixed(2) + '%';
    const settleBadge = o.settlement_only ? '<span style="font-size:8px;padding:1px 5px;border-radius:3px;background:#3a1a1a;color:#ff6b6b;border:1px solid #ff6b6b44;margin-left:4px">SETTLING</span>' : '';
    // Subtle checkmark indicator for dual-exchange availability
    const dualExchMark = '<span style="color:var(--muted);font-size:10px;margin-left:4px">✓</span>';
    const vol = o.volume_24h > 1e9 ? (o.volume_24h/1e9).toFixed(1)+'B'
              : o.volume_24h > 1e6 ? (o.volume_24h/1e6).toFixed(1)+'M'
              : o.volume_24h > 1e3 ? (o.volume_24h/1e3).toFixed(0)+'K' : '—';
    const settleStyle = o.settlement_only ? 'border-left:2px solid #ff4444;opacity:0.6;' : '';
    return `<div class="opp-row ${sel} ${actionable?'actionable':''}" style="${settleStyle}" onclick="selectOpp(${JSON.stringify(o).replace(/"/g,'&quot;')})">
      <div>
        <div class="opp-sym" style="display:flex;align-items:center">${o.symbol}${dualExchMark}${settleBadge}</div>
        <div class="opp-exchs">
          SHORT <span>${o.short_exchange.toUpperCase()}</span> · LONG <span>${o.long_exchange.toUpperCase()}</span>
        </div>
        <div style="display:flex;gap:8px;margin-top:3px;align-items:center">
          <span style="font-size:9px" ${chgCls}>${chgStr}</span>
          <span style="font-size:9px;color:#4a6a8a">$${vol}</span>
          <div class="opp-stability" style="margin-top:0">${stabDots}</div>
        </div>
      </div>
      <div class="opp-right">
        <div class="opp-spread ${cls}">${o.spread_pct.toFixed(4)}%</div>
        <div class="opp-settle">${minsStr} · ${o.settlement_time||''}</div>
      </div>
    </div>`;
  }).join('');
}

function selectOpp(o) {
  selectedOpp = o;
  renderOpps(); // re-render to update selected highlight
  renderDetail(o);
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('detail-content').style.display = 'block';
}

function renderDetail(o) {
  const hasPos = state.positions.length > 0;
  const enterBtn = !hasPos
    ? `<button class="btn-enter" style="margin-top:4px;width:100%;padding:10px" onclick="openModal()" >⚡ Enter Position</button>`
    : `<div style="font-size:10px;color:var(--dim);text-align:center;margin-top:8px">Position active — close it first</div>`;

  const chg = parseFloat(o.change_24h_pct || 0);
  const chgStr = (chg >= 0 ? '+' : '') + chg.toFixed(2) + '%';
  const vol = o.volume_24h > 1e9 ? (o.volume_24h/1e9).toFixed(2)+'B'
              : o.volume_24h > 1e6 ? (o.volume_24h/1e6).toFixed(1)+'M'
              : o.volume_24h.toFixed(0);

  document.getElementById('detail-content').innerHTML = `
    <div class="detail-card">
      <div class="dc-header">
        <span class="dc-title">Opportunity · ${o.symbol}</span>
        <span style="font-size:11px;color:var(--accent)">${o.spread_pct.toFixed(4)}% spread</span>
      </div>
      <div class="dc-body">
        <div class="metric-grid" style="margin-bottom:14px">
          <div class="metric">
            <div class="metric-label">Short Rate</div>
            <div class="metric-val red">${o.short_rate.toFixed(4)}%</div>
          </div>
          <div class="metric">
            <div class="metric-label">Long Rate</div>
            <div class="metric-val green">${o.long_rate.toFixed(4)}%</div>
          </div>
          <div class="metric">
            <div class="metric-label">Net Spread</div>
            <div class="metric-val accent">${o.spread_pct.toFixed(4)}%</div>
          </div>
          <div class="metric">
            <div class="metric-label">Mark Price</div>
            <div class="metric-val">$${parseFloat(o.price).toLocaleString()}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Volume 24h</div>
            <div class="metric-val">$${vol}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Settlement</div>
            <div class="metric-val warn">${o.settlement_time||'—'}</div>
          </div>
        </div>

        <div class="rate-row">
          <div class="rate-exch">
            <div class="exchange-dot dot-dcx"></div>
            <span>${o.short_exchange.toUpperCase()}</span>
            <span class="rate-tag tag-short">SHORT</span>
          </div>
          <div class="rate-val red">${o.short_rate.toFixed(6)}% <span style="color:var(--muted);font-size:10px">per 8h</span></div>
        </div>
        <div class="rate-row">
          <div class="rate-exch">
            <div class="exchange-dot dot-cs"></div>
            <span>${o.long_exchange.toUpperCase()}</span>
            <span class="rate-tag tag-long">LONG</span>
          </div>
          <div class="rate-val green">${o.long_rate.toFixed(6)}% <span style="color:var(--muted);font-size:10px">per 8h</span></div>
        </div>

        ${enterBtn}
      </div>
    </div>

    <div class="detail-card">
      <div class="dc-header"><span class="dc-title">Market Conditions</span></div>
      <div class="dc-body">
        <div class="metric-grid">
          <div class="metric">
            <div class="metric-label">24h Change</div>
            <div class="metric-val ${chg>=0?'green':'red'}">${chgStr}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Interval</div>
            <div class="metric-val accent">${o.interval_hours}h cycle</div>
          </div>
          <div class="metric">
            <div class="metric-label">Stability</div>
            <div class="metric-val">${o.stability_count} scans</div>
          </div>
          <div class="metric">
            <div class="metric-label">Min to Settle</div>
            <div class="metric-val warn">${Math.round(o.minutes_to_settlement)}m</div>
          </div>
        </div>
      </div>
    </div>

    ${renderHistory()}
  `;
}

function formatDateIST(isoString) {
  if (!isoString) return '—';
  try {
    const utc = new Date(isoString);
    // IST is UTC+5:30
    const ist = new Date(utc.getTime() + (5.5 * 60 * 60 * 1000));
    return ist.toLocaleString('en-IN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).replace(/\//g, '-') + ' IST';
  } catch(e) {
    return isoString;
  }
}

function getCloseReasonDisplay(reason) {
  const reasonMap = {
    'EMERGENCY_NEGATIVE_SPREAD': 'Spread Reversal',
    'POST_SETTLEMENT_PROFIT': 'Take Profit (Post-Settlement)',
    'LIQUIDATION_COINDCX': '❌ Liquidated on CoinDCX',
    'LIQUIDATION_COINSWITCH': '❌ Liquidated on CoinSwitch',
    'MANUAL_EXIT': 'Manual Close',
  };
  return reasonMap[reason] || reason.replace(/_/g, ' ');
}

function calculatePerExchangePnL(h) {
  // Calculate P&L on each exchange
  // For closed positions: use entry prices and cumulative funding as proxy
  // Short leg: SHORT exchange (profit if price went DOWN)
  // Long leg: LONG exchange (profit if price went UP)
  
  const qty = parseFloat(h.qty || 0);
  const entrySpread = parseFloat(h.entry_spread || 0);
  const funding = parseFloat(h.cumulative_funding || 0);
  const fee = parseFloat(h.entry_fee_usdt || 0);
  
  // Spread profit = abs(spread) * qty * entry_price (simplified)
  // Since we don't have exit prices stored, use funding as indicator
  // Positive funding = profitable opportunity was captured
  
  const totalFees = fee * 2; // entry + exit
  const grossProfit = funding;
  const netProfit = grossProfit - totalFees;
  
  return {
    shortLegPnL: (entrySpread > 0 ? grossProfit * 0.5 : 0) - (fee), // rough estimate
    longLegPnL: (entrySpread > 0 ? grossProfit * 0.5 : 0) - (fee),
    grossProfit: grossProfit,
    totalFees: totalFees,
    netProfit: netProfit
  };
}

function renderHistory() {
  if (!state.history.length) return '<div class="detail-card"><div class="dc-body" style="text-align:center;color:#4a6a8a;padding:20px">No history yet</div></div>';
  
  const rows = state.history.slice(0, 20).map(h => {
    const action = h.action || 'UNKNOWN';
    const status = h.status || 'PENDING';
    const symbol = h.symbol || '—';
    const qty = h.qty || 0;
    const timestamp = new Date(h.timestamp || Date.now());
    const timeStr = timestamp.toLocaleTimeString('en-IN', {timeZone: 'Asia/Kolkata', hour12: false});
    
    // Determine display based on action
    let actionDisplay = '';
    let details = '';
    let statusColor = 'var(--text)';
    
    if (action === 'ENTRY' || action === 'ENTRY_FAILED') {
      actionDisplay = action === 'ENTRY' ? '🟢 ENTRY' : '🔴 ENTRY FAIL';
      const shortEx = (h.short_exchange || '').toUpperCase();
      const longEx = (h.long_exchange || '').toUpperCase();
      const spread = (h.entry_spread || 0).toFixed(4);
      const shortPrice = (h.short_entry_price || 0).toFixed(6);
      const longPrice = (h.long_entry_price || 0).toFixed(6);
      
      if (action === 'ENTRY_FAILED') {
        details = `${shortEx}→${longEx} | Error: ${h.error || 'Unknown'}`;
        statusColor = 'var(--red)';
      } else {
        details = `SHORT ${shortEx} @ ${shortPrice} | LONG ${longEx} @ ${longPrice} | Spread: ${spread}%`;
        statusColor = 'var(--green)';
      }
    } 
    else if (action === 'EXIT' || action === 'EXIT_FAILED') {
      actionDisplay = action === 'EXIT' ? '⚠️ EXIT' : '🔴 EXIT FAIL';
      const shortEx = (h.short_exchange || '').toUpperCase();
      const longEx = (h.long_exchange || '').toUpperCase();
      const shortOk = h.short_closed ? '✓' : '✗';
      const longOk = h.long_closed ? '✓' : '✗';
      const funding = (h.cumulative_funding || 0).toFixed(4);
      
      if (action === 'EXIT_FAILED') {
        const shortErr = h.short_error ? ` (${h.short_error.substring(0,20)})` : '';
        const longErr = h.long_error ? ` (${h.long_error.substring(0,20)})` : '';
        details = `${shortEx} ${shortOk}${shortErr} | ${longEx} ${longOk}${longErr}`;
        statusColor = 'var(--red)';
      } else {
        details = `${shortEx} ${shortOk} | ${longEx} ${longOk} | Funding: $${funding}`;
        statusColor = 'var(--green)';
      }
    } else if (action === 'LIQUIDATION') {
      actionDisplay = '💥 LIQUIDATION';
      details = h.close_reason || 'Position liquidated';
      statusColor = 'var(--red)';
    } else {
      actionDisplay = action;
      details = h.close_reason || '';
    }
    
    return `<div class="hist-row" style="border-left:3px solid ${statusColor};padding-left:8px">
      <div class="hist-sym" style="color:${statusColor};font-weight:600">${actionDisplay}</div>
      <div class="hist-sym">${symbol}</div>
      <div class="hist-qty">${qty}</div>
      <div class="hist-reason" style="flex:1;font-size:9px;color:#4a6a8a">${details}</div>
      <div class="hist-time" style="font-size:9px;color:#4a6a8a;text-align:right">${timeStr}</div>
    </div>`;
  }).join('');
  
  return `<div class="detail-card">
    <div class="dc-header"><span class="dc-title">Trade History (Last 20)</span></div>
    <div style="font-size:9px;color:#4a6a8a;padding:8px 12px;border-bottom:1px solid var(--border)">
      Action | Symbol | Qty | Details | Time (IST)
    </div>
    <div class="dc-body">${rows}</div>
  </div>`;
}

// ── Render Positions ───────────────────────────────────────────────────────
function renderPositions() {
  const bar = document.getElementById('pos-bar');
  const noPos = document.getElementById('no-pos-msg');
  const container = document.getElementById('pos-container');

  if (!state.positions.length) {
    noPos.style.display = 'flex';
    container.style.display = 'none';
    return;
  }
  noPos.style.display = 'none';
  container.style.display = 'block';

  const posCards = state.positions.map(p => {
    const pnl = parseFloat(p.net_pnl || 0);
    const pnlCls = pnl >= 0 ? 'pos' : 'neg';
    const cum = parseFloat(p.cumulative_funding || 0);
    const entrySpread = parseFloat(p.entry_spread || 0);
    const shortEntry = parseFloat(p.short_entry_price || 0);
    const longEntry = parseFloat(p.long_entry_price || 0);
    const breakEven = parseFloat(p.break_even_usdt || 0);
    const fees = parseFloat(p.entry_fee_usdt || 0);
    const qty = parseFloat(p.qty || 0);

    // Time in position
    const entered = p.entry_time ? new Date(p.entry_time) : null;
    let timeStr = '—';
    if (entered) {
      const mins = Math.floor((Date.now() - entered.getTime()) / 60000);
      timeStr = mins > 60 ? (mins/60).toFixed(1)+'h' : mins+'m';
    }

    // Per-exchange P&L: use live prices from opportunities
    let shortPnL = 0, longPnL = 0;
    const opp = state.opps.find(o => o.symbol === p.symbol);
    if (opp && qty > 0 && shortEntry > 0 && longEntry > 0) {
      const liveShort = parseFloat(opp.short_price || opp.price || 0);
      const liveLong = parseFloat(opp.long_price || opp.price || 0);
      if (liveShort > 0) shortPnL = (shortEntry - liveShort) * qty;
      if (liveLong > 0) longPnL = (liveLong - longEntry) * qty;
    }

    return `<div class="pos-card" data-symbol="${p.symbol}">
      <div style="flex:1">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
          <div class="pos-sym">${p.symbol}</div>
          <span style="font-size:9px;padding:2px 6px;border-radius:3px;background:#1a3a2a;color:var(--green)">${entrySpread>=0?'+':''}${(entrySpread*100).toFixed(4)}% entry</span>
          <span style="font-size:9px;color:#4a6a8a;margin-left:auto">⏱ ${timeStr}</span>
        </div>

        <!-- Per-Exchange Entry Prices & P&L -->
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:10px">
          <!-- SHORT EXCHANGE -->
          <div style="background:rgba(255,64,96,0.08);border:1px solid var(--border2);border-radius:6px;padding:8px">
            <div style="font-size:9px;color:#ff4060;font-weight:700;margin-bottom:4px;letter-spacing:1px">${(p.short_exchange||'').toUpperCase()} · SHORT</div>
            <div style="font-size:8px;color:#4a6a8a;margin-bottom:2px">Entry Price</div>
            <div style="font-size:11px;color:#fff;margin-bottom:6px;font-family:'JetBrains Mono';font-weight:600">$${shortEntry.toFixed(4)}</div>
            <div style="font-size:8px;color:#4a6a8a;margin-bottom:2px">Unrealized P&L</div>
            <div style="font-size:11px;font-weight:600;color:${shortPnL>=0?'var(--green)':'var(--red)'}">${shortPnL>=0?'+':''}$${shortPnL.toFixed(4)}</div>
          </div>
          
          <!-- LONG EXCHANGE -->
          <div style="background:rgba(0,255,157,0.08);border:1px solid var(--border2);border-radius:6px;padding:8px">
            <div style="font-size:9px;color:var(--green);font-weight:700;margin-bottom:4px;letter-spacing:1px">${(p.long_exchange||'').toUpperCase()} · LONG</div>
            <div style="font-size:8px;color:#4a6a8a;margin-bottom:2px">Entry Price</div>
            <div style="font-size:11px;color:#fff;margin-bottom:6px;font-family:'JetBrains Mono';font-weight:600">$${longEntry.toFixed(4)}</div>
            <div style="font-size:8px;color:#4a6a8a;margin-bottom:2px">Unrealized P&L</div>
            <div style="font-size:11px;font-weight:600;color:${longPnL>=0?'var(--green)':'var(--red)'}">${longPnL>=0?'+':''}$${longPnL.toFixed(4)}</div>
          </div>
        </div>

        <!-- Summary Row -->
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:8px">
          <div style="background:var(--bg);border-radius:4px;padding:5px 7px">
            <div style="font-size:8px;color:#4a6a8a;letter-spacing:1px;text-transform:uppercase;margin-bottom:2px">Qty</div>
            <div style="font-size:10px;color:#fff">${qty}</div>
          </div>
          <div style="background:var(--bg);border-radius:4px;padding:5px 7px">
            <div style="font-size:8px;color:#4a6a8a;letter-spacing:1px;text-transform:uppercase;margin-bottom:2px">Fees (×2)</div>
            <div style="font-size:10px;color:#ff9933">$${(fees*2).toFixed(4)}</div>
          </div>
          <div style="background:var(--bg);border-radius:4px;padding:5px 7px">
            <div style="font-size:8px;color:#4a6a8a;letter-spacing:1px;text-transform:uppercase;margin-bottom:2px">Funding</div>
            <div style="font-size:10px;color:var(--green)">$${cum.toFixed(4)}</div>
          </div>
          <div style="background:var(--bg);border-radius:4px;padding:5px 7px">
            <div style="font-size:8px;color:#4a6a8a;letter-spacing:1px;text-transform:uppercase;margin-bottom:2px">Break Even</div>
            <div style="font-size:10px;color:var(--warn)">$${breakEven.toFixed(4)}</div>
          </div>
        </div>
      </div>

      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px;margin-left:16px">
        <div style="text-align:right">
          <div class="pnl-val ${pnlCls}" style="font-size:18px">${pnl>=0?'+':''}$${pnl.toFixed(4)}</div>
          <div class="pnl-label">Net P&L</div>
        </div>
        <button class="btn-close-pos" onclick="closePosition('${p.symbol}')" title="Quick exit this position (E key)" style="${p.closing?'opacity:0.5;cursor:wait':''}">
          ${p.closing ? '⏳ CLOSING...' : '✕ EXIT'}
        </button>
      </div>
    </div>`;
  }).join('');
  
  // Add "Close All" button header for multiple positions
  const closeAllBtn = state.positions.length > 1 
    ? `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;margin-bottom:10px;border-bottom:1px solid var(--border)">
         <div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px">${state.positions.length} Active Position${state.positions.length>1?'s':''}</div>
         <button class="btn-close-pos" onclick="emergencyCloseAll()" style="margin:0;border-color:var(--red);color:var(--red);font-weight:700" title="Close all positions (X key)">🚨 CLOSE ALL</button>
       </div>`
    : `<div style="font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;padding:0 0 10px 0;margin-bottom:10px;border-bottom:1px solid var(--border)">1 Active Position</div>`;
  
  container.innerHTML = closeAllBtn + posCards;
}

// ── Modal ─────────────────────────────────────────────────────────────────
function calcPositionValue() {
  const o = selectedOpp;
  if (!o) return;
  const qty = parseFloat(document.getElementById('m-qty').value) || 0;
  const price = parseFloat(o.price || o.mark_price || 0);
  const leverage = parseFloat(document.getElementById('m-lev').value) || 1;
  if (qty > 0 && price > 0 && leverage > 0) {
    const val = (qty * price) / leverage;  // Position Value = (qty × price) / leverage
    document.getElementById('modal-pos-value').textContent = '$' + val.toFixed(2);
  } else {
    document.getElementById('modal-pos-value').textContent = '—';
  }
}

async function updateQtyRange() {
  const o = selectedOpp;
  if (!o) return;
  
  const lev = parseFloat(document.getElementById('m-lev').value) || 1;
  
  try {
    const r = await authFetch(`/api/trade/qty-range?symbol=${o.symbol}&leverage=${Math.floor(lev)}&short_exchange=${o.short_exchange}&long_exchange=${o.long_exchange}`);
    const d = await r.json();
    
    if (d.success) {
      // Update qty range display
      document.getElementById('modal-min-qty').textContent = d.min_qty;
      document.getElementById('modal-max-qty').textContent = d.max_qty;
      document.getElementById('m-qty').max = d.max_qty;
      
      // Update exchange labels
      document.getElementById('modal-short-ex').textContent = d.exchanges.short.toUpperCase();
      document.getElementById('modal-long-ex').textContent = d.exchanges.long.toUpperCase();
      document.getElementById('modal-short-ex2').textContent = d.exchanges.short.toUpperCase();
      document.getElementById('modal-long-ex2').textContent = d.exchanges.long.toUpperCase();
      
      // Update balance info
      document.getElementById('modal-bal-short').textContent = d.balances.short;
      document.getElementById('modal-bal-long').textContent = d.balances.long;
      
      // Update hint
      if (d.max_qty === 0) {
        document.getElementById('modal-qty-hint').textContent = '❌ Insufficient balance';
        document.getElementById('modal-qty-hint').style.color = 'var(--red)';
      } else if (d.min_qty > d.max_qty) {
        document.getElementById('modal-qty-hint').textContent = `❌ Insufficient balance — need ${(d.min_qty * d.price / d.leverage).toFixed(2)} USDT but have $${(d.balances.short + d.balances.long).toFixed(2)}`;
        document.getElementById('modal-qty-hint').style.color = 'var(--red)';
      } else {
        document.getElementById('modal-qty-hint').textContent = `Both sides same quantity — Minimum: ${d.min_qty}`;
        document.getElementById('modal-qty-hint').style.color = 'var(--muted)';
      }
      
      // Auto-fill qty with MIN qty if blank
      if (!document.getElementById('m-qty').value) {
        const autoQty = Math.floor(d.min_qty);
        if (autoQty <= d.max_qty && autoQty > 0) {
          document.getElementById('m-qty').value = autoQty;
          calcPositionValue();
        }
      }
    } else {
      document.getElementById('modal-qty-hint').textContent = d.error || 'Could not fetch qty range';
      document.getElementById('modal-qty-hint').style.color = 'var(--red)';
    }
  } catch(e) {
    console.error('updateQtyRange error:', e);
    document.getElementById('modal-qty-hint').textContent = 'Network error loading qty range';
    document.getElementById('modal-qty-hint').style.color = 'var(--red)';
  }
}

function openModal() {
  if (selectedOpp && selectedOpp.settlement_only) {
    toast('This pair is in settlement-only mode — entry blocked', 'error');
    return;
  }
  if (!selectedOpp) return;
  const o = selectedOpp;
  document.getElementById('modal-title').textContent = `Place Arbitrage Order: ${o.symbol}`;
  document.getElementById('modal-info').innerHTML = `Spread <span style="color:var(--green)">${o.spread_pct.toFixed(4)}%</span> | Settle ${o.settlement_time||'—'} | Price $${parseFloat(o.price).toLocaleString('en-US', {maximumFractionDigits: 6})}`;
  document.getElementById('modal-msg').style.display = 'none';
  document.getElementById('m-qty').value = '';
  document.getElementById('m-lev').value = '1';
  document.getElementById('modal-overlay').classList.add('open');
  updateQtyRange();
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

async function confirmEntry() {
  const o = selectedOpp;
  if (!o) return;
  
  const qty = parseFloat(document.getElementById('m-qty').value);
  const lev = parseInt(document.getElementById('m-lev').value) || 1;
  const minQty = parseFloat(document.getElementById('modal-min-qty').textContent);
  const maxQty = parseFloat(document.getElementById('modal-max-qty').textContent);
  
  // Validate qty
  if (!qty || qty <= 0) {
    document.getElementById('modal-msg').textContent = '❌ Enter a valid quantity';
    document.getElementById('modal-msg').style.display = 'block';
    return;
  }
  
  if (qty < minQty) {
    document.getElementById('modal-msg').textContent = `❌ Qty ${qty} below minimum ${minQty}`;
    document.getElementById('modal-msg').style.display = 'block';
    return;
  }
  
  if (qty > maxQty) {
    document.getElementById('modal-msg').textContent = `❌ Qty ${qty} exceeds maximum ${maxQty}`;
    document.getElementById('modal-msg').style.display = 'block';
    return;
  }
  
  const btn = document.getElementById('btn-confirm-enter');
  btn.textContent = '⏳ Submitting…'; btn.disabled = true;

  try {
    const r = await authFetch('/api/trade/enter', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        symbol: o.symbol,
        short_exchange: o.short_exchange,
        long_exchange: o.long_exchange,
        qty: qty,
        leverage: lev,
      })
    });
    const d = await r.json();
    if (d.success) {
      // ASYNC ENTRY - position will appear via WebSocket
      closeModal();
      toast('⚡ ORDER SENT - Filling in background (watch for position...)', 'success');
    } else {
      document.getElementById('modal-msg').textContent = d.error || 'Entry failed';
      document.getElementById('modal-msg').style.display = 'block';
    }
  } catch(e) {
    document.getElementById('modal-msg').textContent = 'Network error: ' + e.message;
    document.getElementById('modal-msg').style.display = 'block';
  }
  btn.textContent = '⚡ Enter Position'; btn.disabled = false;
}

async function closePosition(symbol) {
  // Find and remove position immediately (millisecond trading)
  const idx = state.positions.findIndex(p => p.symbol === symbol);
  if (idx === -1) return;
  
  const pos = state.positions[idx];
  state.positions.splice(idx, 1);  // Remove immediately
  renderPositions();
  toast('✓ Position closed', 'success');
  
  // Fire close in background (don't wait)
  try {
    const r = await authFetch(`/api/trade/exit/${symbol}`, {method:'POST'});
    const d = await r.json();
    
    if (!d.success) {
      // If backend says failure, re-add the position
      state.positions.push(pos);
      renderPositions();
      toast('⚠ Close failed: ' + (d.error || 'unknown'), 'error');
    } else {
      toast('✓ Close order executing on exchanges', 'success');
    }
  } catch(e) {
    // Network error - re-add position
    state.positions.push(pos);
    renderPositions();
    toast('⚠ Network error: ' + e.message, 'error');
  }
}

async function quickEntry() {
  if (!selectedOpp) { toast('Select a pair first', 'error'); return; }
  const o = selectedOpp;
  if (o.settlement_only) { toast('Settlement-only mode — entry blocked', 'error'); return; }
  if (state.positions.length > 0) { toast('Close active position first', 'error'); return; }
  
  try {
    // Fetch min qty
    const qtyRes = await authFetch(`/api/trade/qty-range?symbol=${o.symbol}`);
    const qtyData = await qtyRes.json();
    const minQty = parseFloat(qtyData.min_qty || 1);
    
    const r = await authFetch('/api/trade/enter', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        symbol: o.symbol,
        short_exchange: o.short_exchange,
        long_exchange: o.long_exchange,
        qty: minQty,
        leverage: 1,
      })
    });
    const d = await r.json();
    if (d.success) {
      toast(`✅ Quick Entry: ${minQty} @ ${o.spread_pct.toFixed(4)}% spread`, 'success');
    } else {
      toast('Entry failed: ' + (d.error||''), 'error');
    }
  } catch(e) { toast('Network error: ' + e.message, 'error'); }
}

async function emergencyCloseAll() {
  if (state.positions.length === 0) { toast('No active positions', 'info'); return; }
  
  const posSymbols = state.positions.map(p => p.symbol).join(', ');
  
  // Show custom confirm modal
  document.getElementById('confirm-title').textContent = '🚨 EMERGENCY CLOSE ALL';
  document.getElementById('confirm-msg').textContent = `Close ALL ${state.positions.length} position${state.positions.length>1?'s':''}?\n\n${posSymbols}`;
  document.getElementById('confirm-btn').style.borderColor = 'var(--red)';
  document.getElementById('confirm-btn').style.background = 'rgba(255,64,96,0.9)';
  document.getElementById('confirm-modal').classList.add('show');
  
  // Store callback for execution
  window.confirmCallback = async () => {
    // Save positions before clearing
    const closingPositions = [...state.positions];
    
    // CLEAR IMMEDIATELY (millisecond response)
    state.positions = [];
    renderPositions();
    toast('⚡ ALL POSITIONS CLEARED - Closing on exchanges...', 'success');
    
    // Send close requests for all (don't wait)
    const closePromises = closingPositions.map(pos =>
      authFetch(`/api/trade/exit/${pos.symbol}`, {method:'POST'})
        .then(r => r.json())
        .catch(e => ({success: false, error: e.message}))
    );
    
    // Fire and forget (don't wait for all)
    Promise.allSettled(closePromises).then(results => {
      let failCount = 0;
      results.forEach(r => {
        if (r.status === 'rejected' || (r.status === 'fulfilled' && !r.value.success)) {
          failCount++;
        }
      });
      if (failCount > 0) {
        toast(`⚠ ${failCount} position(s) had issues - check logs`, 'warn');
      } else {
        toast('✓ All positions closed on exchanges', 'success');
      }
    });
  };
}

function closeConfirmModal() {
  document.getElementById('confirm-modal').classList.remove('show');
  document.getElementById('confirm-btn').style.background = '#0066ff';
  window.confirmCallback = null;
}

async function executeConfirm() {
  if (window.confirmCallback) {
    await window.confirmCallback();
  }
  closeConfirmModal();
}

// ── Admin toggles ──────────────────────────────────────────────────────────
async function toggleAuto() {
  const r = await authFetch('/api/auto/toggle', {method:'POST'});
  const d = await r.json();
  state.autoMode = d.auto_mode;
  updateModeBadge();
  toast('Auto mode: ' + (d.auto_mode ? 'ON' : 'OFF'), 'info');
}

function updateModeBadge() {
  const autoBtn = document.getElementById('btn-auto');
  if (state.autoMode) {
    autoBtn.style.borderColor = 'var(--green)';
    autoBtn.style.color = 'var(--green)';
  } else {
    autoBtn.style.borderColor = 'var(--purple)';
    autoBtn.style.color = 'var(--purple)';
  }
}

function showHistory() {
  const detailContent = document.getElementById('detail-content');
  const emptyState = document.getElementById('empty-state');
  
  // Hide empty state
  emptyState.style.display = 'none';
  
  // Show history
  detailContent.innerHTML = renderHistory();
  detailContent.style.display = 'block';
  
  // Scroll to history
  detailContent.scrollIntoView({behavior: 'smooth'});
}

// ── Helpers ────────────────────────────────────────────────────────────────
async function authFetch(url, opts={}) {
  opts.headers = opts.headers || {};
  opts.headers['Authorization'] = 'Bearer ' + token;
  const r = await fetch(url, opts);
  if (r.status === 401) {
    localStorage.clear();
    window.location.href = '/login';
    throw new Error('Session expired');
  }
  return r;
}

let _toastTimer;
function toast(msg, type='info') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'show t-' + type;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { el.className = ''; }, 3500);
}

function doLogout() {
  localStorage.clear();
  window.location.href = '/login';
}

// Close modal on overlay click
document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
});

// Keyboard shortcuts for ultra-fast trading
document.addEventListener('keydown', (e) => {
  if (e.target === document.body || e.target.id === 'detail' || e.target.classList.contains('modal')) {
    if ((e.key === 'q' || e.key === 'Q') && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      if (selectedOpp) openModal();
      else toast('Select a pair first', 'info');
    }
    if ((e.key === 'e' || e.key === 'E') && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      if (state.positions.length > 0) {
        closePosition(state.positions[0].symbol);
      } else {
        toast('No active position to exit', 'info');
      }
    }
    if ((e.key === 'x' || e.key === 'X') && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      emergencyCloseAll();
    }
  }
});

updateModeBadge();
connect();
