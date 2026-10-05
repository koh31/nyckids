let events = [];

function score(e){
  let s = 0;
  if(e.price_type==="free") s+=2;
  if(e.area==="Manhattan") s+=2;
  if(e.source && e.source.includes("Parks")) s+=1;
  return s;
}

function renderCard(e){
  return `
  <div class="card">
    <h3>${e.title}</h3>

    <div class="meta">
      ${e.date || ""} ・ ${e.area || ""}
    </div>

    <div>
      ${e.price_type==="free" ? '<span class="tag">FREE</span>' : ''}
      <span class="tag">${e.source || ""}</span>
    </div>

    <a class="cta" href="${e.url}" target="_blank">
      🎟️ Get Tickets
    </a>
  </div>
  `;
}

function render(){
  // 全イベント
  document.getElementById("eventsGrid").innerHTML =
    events.map(renderCard).join("");

  // おすすめ
  const top = [...events]
    .sort((a,b)=>score(b)-score(a))
    .slice(0,5);

  document.getElementById("featuredList").innerHTML =
    top.map(renderCard).join("");
}

fetch("./data/events.json")
  .then(r=>r.json())
  .then(d=>{
    events = d.events;
    render();
  });
