let structured = null;

const $ = (id) => document.getElementById(id);
const fmt = (iso) => iso ? new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso)) : 'Chưa rõ';
const escapeHtml = (s='') => String(s).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\'':'&#39;','"':'&quot;'}[c]));

async function getJSON(url, options={}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function item({title, content, time, channel, author, status, level, href, extra}) {
  return `<div class="item">
    <h3>${escapeHtml(title || 'Không có tiêu đề')}</h3>
    ${content ? `<p>${escapeHtml(content)}</p>` : ''}
    ${extra ? `<p class="extra">${escapeHtml(extra)}</p>` : ''}
    <div class="meta">
      ${status ? `<span class="badge ${status}">${status}</span>` : ''}
      ${level ? `<span class="badge ${level}">${level}</span>` : ''}
      ${time ? `<span class="badge">${fmt(time)}</span>` : ''}
      ${channel ? `<span class="badge">#${escapeHtml(channel)}</span>` : ''}
      ${author ? `<span class="badge">${escapeHtml(author)}</span>` : ''}
      ${href ? `<a class="badge" href="${escapeHtml(href)}" target="_blank">link</a>` : ''}
    </div>
  </div>`;
}

function renderStats(stats) {
  $('stats').innerHTML = Object.entries(stats || {}).map(([k,v]) =>
    `<div class="stat-card"><span>${escapeHtml(k)}</span><strong>${v}</strong></div>`
  ).join('');
}

function renderStructured(data) {
  structured = data;
  renderStats(data.stats);
  $('deadlineCount').textContent = `${data.deadlines?.length || 0} mục`;
  $('deadlines').innerHTML = (data.deadlines || []).map(d => item({
    title: d.title, content: d.content, time: d.deadline_at, channel: d.channel, author: d.author, status: d.status, extra: d.priority ? `priority: ${d.priority}` : ''
  })).join('') || '<p class="empty">Không có deadline.</p>';

  $('announcements').innerHTML = (data.announcements || []).map(a => item({
    title: a.title || 'Thông báo', content: a.content,
    time: a.message_time, channel: a.channel, author: a.author, status: a.priority
  })).join('') || '<p class="empty">Không có thông báo.</p>';

  $('meetings').innerHTML = (data.meetings || []).map(m => item({
    title: m.title, content: m.content, time: m.meeting_at, channel: m.channel, author: m.author, status: m.status, href: m.meeting_link,
    extra: [m.platform, m.meeting_id ? `ID ${m.meeting_id}` : '', m.passcode ? `Passcode ${m.passcode}` : ''].filter(Boolean).join(' • ')
  })).join('') || '<p class="empty">Không có meeting.</p>';

  const resourceItems = [ ...(data.resources || []).map(r => ({title:r.title, content:r.url, time:r.message_time, channel:r.channel, author:r.author, href:r.url, extra: r.kind})),
    ...(data.documents || []).map(d => ({title:d.name, content:d.url, time:d.message_time, channel:d.channel, author:d.author, href:d.url, extra: d.kind})) ];
  $('resources').innerHTML = resourceItems.map(item).join('') || '<p class="empty">Không có tài nguyên.</p>';
  $('questions').innerHTML = (data.questions || []).map(q => item({
    title: q.title || 'Câu hỏi', content: q.question || q.content, time: q.message_time, channel: q.channel, author: q.author, status: q.answered ? 'answered' : 'open'
  })).join('') || '<p class="empty">Không có câu hỏi.</p>';
  $('jsonView').textContent = JSON.stringify(data, null, 2);
}

function renderSearch(results) {
  $('searchCount').textContent = `${results.count || 0} kết quả`;
  $('searchResults').innerHTML = (results.results || []).map(r => {
    const i = r.item || {};
    return item({
      title: `${i.section || 'item'}: ${i.title || i.name || i.id || 'Không tiêu đề'}`,
      content: i.content || i.question || i.url || '',
      time: i.deadline_at || i.meeting_at || i.message_time,
      channel: i.channel,
      author: i.author,
      status: i.status,
      extra: `score: ${r.score ?? 0}`
    });
  }).join('') || '<p class="empty">Không có kết quả tìm kiếm.</p>';
}

async function renderReminders() {
  const hours = $('hoursSelect').value;
  const data = await getJSON(`/api/reminders?hours=${hours}`);
  $('reminderWindow').textContent = `${hours} giờ`;
  $('reminders').innerHTML = (data.reminders || []).map(r => item({
    title: r.message, time: r.deadline_at, level: r.level, status: r.level
  })).join('') || '<p class="empty">Không có deadline trong khung thời gian này.</p>';
}

async function refresh({force=false, llm=false} = {}) {
  $('jsonView').textContent = 'Loading...';
  const data = await getJSON(`/api/structured?refresh=${force ? 1 : 0}&llm=${llm ? 1 : 0}`);
  renderStructured(data);
  await renderReminders();
  const latest = await getJSON('/api/deadlines/latest');
  const itemData = latest.item;
  $('latestDeadlineState').textContent = itemData ? `${itemData.status} • ${itemData.hours_left} giờ` : 'no deadline';
  $('latestDeadline').innerHTML = itemData ? item({
    title: itemData.title,
    content: itemData.content,
    time: itemData.deadline_at,
    channel: itemData.channel,
    author: itemData.author,
    status: itemData.status,
    extra: latest.message
  }) : '<p class="empty">Không tìm thấy deadline.</p>';
}

async function tick() {
  try {
    const t = await getJSON('/api/time');
    $('now').textContent = `${t.date} ${t.time}`;
  } catch { /* ignore */ }
}

async function doSearch() {
  const q = $('searchInput').value.trim();
  const section = $('sectionSelect').value;
  const url = new URL('/api/search', window.location.origin);
  if (q) url.searchParams.set('q', q);
  if (section) url.searchParams.set('section', section);
  const data = await getJSON(url.toString());
  renderSearch(data);
}

async function askAgent(question) {
  const q = question || $('qaInput').value.trim();
  if (!q) return;
  $('qaAnswer').textContent = 'Đang suy nghĩ...';
  const data = await getJSON('/api/qa?q=' + encodeURIComponent(q));
  $('qaAnswer').textContent = `${data.answer}\n\n--- tool trace ---\n${JSON.stringify(data.tool_trace, null, 2)}`;
}

$('refreshBtn').onclick = () => refresh({force:true});
$('llmBtn').onclick = () => refresh({force:true, llm:true});
$('hoursSelect').onchange = renderReminders;
$('searchBtn').onclick = doSearch;
$('searchInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch(); });
$('qaBtn').onclick = () => askAgent();
$('askSampleBtn').onclick = () => {
  $('qaInput').value = 'Deadline gần nhất là gì?';
  askAgent('Deadline gần nhất là gì?');
};
$('clearQaBtn').onclick = () => { $('qaInput').value = ''; $('qaAnswer').textContent = 'Agent sẽ trả lời ở đây...'; };
$('copyJson').onclick = async () => {
  await navigator.clipboard.writeText(JSON.stringify(structured, null, 2));
  $('copyJson').textContent = 'Copied!';
  setTimeout(() => $('copyJson').textContent = 'Copy JSON', 1200);
};

tick(); setInterval(tick, 1000);
refresh();
doSearch();
