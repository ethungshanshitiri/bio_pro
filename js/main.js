const siteConfig = {
  scholarProfileUrl: "https://scholar.google.com/citations?user=pbAP-VQAAAAJ&hl=en",
  orcidId: "0000-0002-8696-0920"
};

function byId(id){
  return document.getElementById(id);
}

function escapeHtml(str){
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setProfileLinks(){
  const scholar = byId("scholarLink");
  const orcid = byId("orcidLink");

  if (siteConfig.scholarProfileUrl){
    scholar.href = siteConfig.scholarProfileUrl;
    scholar.textContent = "Open profile";
  } else {
    scholar.href = "#";
    scholar.textContent = "https://scholar.google.com/citations?user=pbAP-VQAAAAJ&hl=en";
  }

  if (siteConfig.orcidId){
    const url = `https://orcid.org/${siteConfig.orcidId}`;
    orcid.href = url;
    orcid.textContent = siteConfig.orcidId;
  } else {
    orcid.href = "#";
    orcid.textContent = "Add your ORCID";
  }
}

async function loadPublications(){
  const url = `data/publications.json?v=${Date.now()}`;
  const res = await fetch(url);
  if (!res.ok){
    throw new Error("Could not load publications.json");
  }
  return await res.json();
}

function renderPublications(pubData, tabKey){
  const list = byId("pubList");
  list.innerHTML = "";

  const groups = {
    journals: pubData.journals || [],
    conferences: pubData.conferences || [],
    book_chapters: pubData.book_chapters || []
  };

  const items = groups[tabKey] || [];

  items.forEach((it) => {
    const li = document.createElement("li");
    li.className = "pub-item";

    const tag = document.createElement("div");
    tag.className = "pub-tag";
    tag.textContent = it.label;

    const body = document.createElement("div");
    const cit = document.createElement("div");
    cit.className = "pub-cit";
    cit.innerHTML = escapeHtml(it.citation);

    body.appendChild(cit);

    const links = document.createElement("div");
    links.className = "pub-links";

    if (it.url){
      const a = document.createElement("a");
      a.href = it.url;
      a.target = "_blank";
      a.rel = "noreferrer";
      a.textContent = "DOI";
      links.appendChild(a);
    }

    body.appendChild(links);

    li.appendChild(tag);
    li.appendChild(body);
    list.appendChild(li);
  });

  const updated = byId("pubUpdated");
  if (pubData.generated_utc){
    updated.textContent = `Last updated ${pubData.generated_utc.replace("T", " ").replace("Z", " UTC")}`;
  } else {
    updated.textContent = "";
  }
}

function initTabs(pubData){
  const tabs = Array.from(document.querySelectorAll(".tab"));
  let active = "journals";

  const setActive = (key) => {
    active = key;
    tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === key));
    renderPublications(pubData, active);
  };

  tabs.forEach((t) => {
    t.addEventListener("click", () => setActive(t.dataset.tab));
  });

  setActive(active);
}

async function main(){
  byId("year").textContent = String(new Date().getFullYear());
  setProfileLinks();

  try{
    const pubData = await loadPublications();
    initTabs(pubData);
  }catch(e){
    const list = byId("pubList");
    list.innerHTML = "<li class='pub-item'><div class='pub-tag'>info</div><div class='pub-cit'>Publications could not be loaded. Check data/publications.json.</div></li>";
  }
}

main();
