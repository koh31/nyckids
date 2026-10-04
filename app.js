
const state = { events: [], quick: "all" };
const $ = (s) => document.querySelector(s);

const palette = {
  art:"#ffd7df", story:"#d7ebff", science:"#dbf3e6", music:"#fff0b9",
  outdoor:"#d9f4c8", museum:"#e9ddff", general:"#e8eef6"
};
const icons = {
  art:"🎨", story:"📚", science:"🔬", music:"🎵", outdoor:"🌳",
  museum:"🏛️", dance:"🩰", food:"🥣", general:"✨"
};

function parseNYDate(dateStr) {
  return new Date(dateStr + "T12:00:00");
}
function weekendRange() {
  const now = new Date();
  const day = now.getDay();
  const daysUntilSat = (6 - day + 7) % 7;
  const sat = new Date(now); sat.setHours(0,0,0,0); sat.setDate(now.getDate()+daysUntilSat);
  const sun = new Date(sat); sun.setDate(sat.getDate()+1); sun.setHours(23,59,59,999);
  return [sat,sun];
}
function isWeekendEvent(e){
  const [sat,sun]=weekendRange(), d=parseNYDate(e.date);
  return d>=sat && d<=sun;
}
function ageMatch(e, selected){
  if(selected==="all") return true;
  if(selected==="all-ages") return e.age_group==="all-ages";
  return e.age_group===selected || e.age_group==="all-ages";
}
function render(){
  const borough=$("#boroughFilter").value;
  const age=$("#ageFilter").value;
  const price=$("#priceFilter").value;
  const q=$("#searchInput").value.trim().toLowerCase();

  let items = state.events.filter(e => {
    if(borough!=="all" && e.borough!==borough) return false;
    if(!ageMatch(e,age)) return false;
    if(price!=="all" && e.price_type!==price) return false;
    if(q && !(`${e.title} ${e.description||""} ${e.venue||""} ${(e.tags||[]).join(" ")}`.toLowerCase().includes(q))) return false;
    if(state.quick==="free" && e.price_type!=="free") return false;
    if(state.quick==="weekend" && !isWeekendEvent(e)) return false;
    if(state.quick==="0-5" && !ageMatch(e,"0-5")) return false;
    if(state.quick==="6-12" && !ageMatch(e,"6-12")) return false;
    return true;
  }).sort((a,b)=> (a.date+a.time).localeCompare(b.date+b.time));

  $("#resultCount").textContent = `${items.length} events`;
  $("#emptyState").classList.toggle("hidden", items.length>0);
  $("#eventsGrid").innerHTML = items.map(cardHTML).join("");
}
function cardHTML(e){
  const d = parseNYDate(e.date);
  const mon = d.toLocaleDateString("en-US",{month:"short"}).toUpperCase();
  const day = d.getDate();
  const cat=e.category||"general";
  const safeUrl = e.url && /^https?:\/\//.test(e.url) ? e.url : "#";
  return `
  <article class="event-card">
    <div class="event-visual" style="background:${palette[cat]||palette.general}">
      <div class="event-icon">${icons[cat]||icons.general}</div>
      <div class="date-badge"><b>${day}</b><span>${mon}</span></div>
    </div>
    <div class="event-body">
      <div class="tags">
        ${(e.price_type==="free"?'<span class="tag">FREE</span>':'')}
        <span class="tag">${e.borough}</span>
        <span class="tag">${e.age_label||"Kids"}</span>
      </div>
      <h3>${escapeHtml(e.title)}</h3>
      <div class="meta">
        <div>🕒 <span>${escapeHtml(e.time||"時間は公式サイトで確認")}</span></div>
        <div>📍 <span>${escapeHtml(e.venue||"NYC")}</span></div>
      </div>
      <p class="desc">${escapeHtml(e.description||"")}</p>
      <div class="event-foot">
        <span class="source">${escapeHtml(e.source||"Official source")}</span>
        <a class="more" href="${safeUrl}" target="_blank" rel="noopener noreferrer">公式サイト ↗</a>
      </div>
    </div>
  </article>`;
}
function escapeHtml(v=""){return v.replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));}

async function boot(){
  try{
    const res = await fetch("./data/events.json",{cache:"no-store"});
    const data = await res.json();
    state.events = data.events || [];
    $("#updatedAt").textContent = `最終更新: ${new Date(data.updated_at).toLocaleString("ja-JP",{dateStyle:"medium",timeStyle:"short"})}`;
    render();
  }catch(err){
    $("#updatedAt").textContent="イベントデータを読み込めませんでした";
    console.error(err);
  }
}
["boroughFilter","ageFilter","priceFilter"].forEach(id=>$("#"+id).addEventListener("change",render));
$("#searchInput").addEventListener("input",render);
document.querySelectorAll(".quick-chip").forEach(btn=>btn.addEventListener("click",()=>{
  document.querySelectorAll(".quick-chip").forEach(x=>x.classList.remove("active"));
  btn.classList.add("active"); state.quick=btn.dataset.quick; render();
}));
$("#todayBtn").addEventListener("click",()=>{
  const today = new Date().toISOString().slice(0,10);
  state.quick="all";
  document.querySelectorAll(".quick-chip").forEach(x=>x.classList.remove("active"));
  document.querySelector('[data-quick="all"]').classList.add("active");
  const original = state.events;
  const todays = original.filter(e=>e.date===today);
  $("#events").scrollIntoView();
  if(todays.length){
    const keep=state.events; state.events=todays; render();
    setTimeout(()=>{state.events=keep},0);
  } else {
    render();
    alert("今日の掲載イベントはまだありません。今後の日程をご覧ください。");
  }
});
boot();
