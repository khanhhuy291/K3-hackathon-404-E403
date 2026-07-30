let structured = null;

const $ = (id) => document.getElementById(id);
const fmt = (iso) => iso ? new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso)) : 'Chưa rõ';
const escapeHtml = (s='') => String(s).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function item({title, content, time, channel, author, status, level, href}) {
  return `<div class="item">
    <h3>${escapeHtml(title || 'Không có tiêu đề')}</h3>
    ${content ? `<p>${escapeHtml(content)}</p>` : ''}
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
    title: d.title, content: d.content, time: d.deadline_at, channel: d.channel, author: d.author, status: d.status
  })).join('') || '<p class="empty">Không có deadline.</p>';

  $('announcements').innerHTML = (data.announcements || []).map(a => item({
    title: a.priority === 'high' ? 'Thông báo quan trọng' : 'Thông báo', content: a.content,
    time: a.message_time, channel: a.channel, author: a.author, status: a.priority
  })).join('') || '<p class="empty">Không có thông báo.</p>';

  $('meetings').innerHTML = (data.meetings || []).map(m => item({
    title: m.title, content: m.content, time: m.meeting_at, channel: m.channel, author: m.author, status: m.status, href: m.meeting_link
  })).join('') || '<p class="empty">Không có meeting.</p>';

  const resourceItems = [ ...(data.resources || []).map(r => ({title:r.title, content:r.url, time:r.message_time, channel:r.channel, author:r.author, href:r.url})),
    ...(data.documents || []).map(d => ({title:d.name, content:d.url, time:d.message_time, channel:d.channel, author:d.author, href:d.url})) ];
  $('resources').innerHTML = resourceItems.map(item).join('') || '<p class="empty">Không có tài nguyên.</p>';
  $('jsonView').textContent = JSON.stringify(data, null, 2);
}

async function renderReminders() {
  const hours = $('hoursSelect').value;
  const data = await getJSON(`/api/reminders?hours=${hours}`);
  $('reminderWindow').textContent = `${hours} giờ`;
  $('reminders').innerHTML = (data.reminders || []).map(r => item({
    title: r.message, time: r.deadline_at, level: r.level
  })).join('') || '<p class="empty">Không có deadline trong khung thời gian này.</p>';
}

async function refresh({force=false, llm=false} = {}) {
  $('jsonView').textContent = 'Loading...';
  const data = await getJSON(`/api/structured?refresh=${force ? 1 : 0}&llm=${llm ? 1 : 0}`);
  renderStructured(data);
  await renderReminders();
}

async function tick() {
  try {
    const t = await getJSON('/api/time');
    $('now').textContent = `${t.date} ${t.time}`;
  } catch { /* ignore */ }
}

$('refreshBtn').onclick = () => refresh({force:true});
$('llmBtn').onclick = () => refresh({force:true, llm:true});
$('hoursSelect').onchange = renderReminders;
$('copyJson').onclick = async () => {
  await navigator.clipboard.writeText(JSON.stringify(structured, null, 2));
  $('copyJson').textContent = 'Copied!';
  setTimeout(() => $('copyJson').textContent = 'Copy JSON', 1200);
};

tick(); setInterval(tick, 1000);
refresh();
