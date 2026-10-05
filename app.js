let events = [];

function score(e){
  let s = 0;
  if(e.price_type==="free") s+=2;
  if(e.area==="Manhattan") s+=2;
  return s;
}

function applyFilters(list){
  const age = document.getElementById("ageFilter").value;
  const genre = document.getElementById("genreFilter").value;

  return list.filter(e=>{
    if(age && e.age_group !== age) return false;
    if(genre && e.genre !== genre) return false;
    return true;
  });
}

function renderCard(e){
  return `
  <div class="card">
    <h3>${e.title}</h3>

    <div class="meta">
      ${e.date || ""} ・ ${e.area || ""}
    </div>

    <div style="font-size:13px; margin:6px 0;">
      ${e.ja_desc || ""}
    </div>

    <div>
      <span class="tag">${e.age_group || ""}</span>
      <span class="tag">${e.genre || ""}</span>
    </div>

    <a class="cta" href="${e.url}" target="_blank">
      詳細を見る
    </a>
  </div>
  `;
}

function render(){
  const filtered = applyFilters(events);

  document.getElementById("eventsGrid").innerHTML =
    filtered.map(renderCard).join("");

  const top = [...filtered]
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

document.getElementById("ageFilter").addEventListener("change", render);
document.getElementById("genreFilter").addEventListener("change", render);
