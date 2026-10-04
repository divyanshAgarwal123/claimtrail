"use strict";

const state = {items: [], activeId: null, episode: null, activeUnit: null, dirty: false, source: null,
  revision: null, editVersion: 0, episodeRequest: 0, searchRequest: 0, turnRequest: 0, saving: false, loading: false};
const $ = (selector, base = document) => base.querySelector(selector);
const $$ = (selector, base = document) => Array.from(base.querySelectorAll(selector));

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}

function node(tag, className = "", text = "") {
  const e = document.createElement(tag);
  if (className) e.className = className;
  e.textContent = text;
  return e;
}

function markDirty() {
  state.editVersion++;
  state.dirty = true;
  $("#save-status").textContent = "Unsaved edits";
  $("#summary-save-state").textContent = "Unsaved edits are not reflected in this overview.";
  updateReadiness();
}

function reviewState(item) {
  if (!item.total_units) return "unreviewed";
  return item.labeled_units === item.total_units ? "complete" : "partial";
}

function updateNavigation() {
  const nav = $("#episode-list");
  nav.replaceChildren();
  const query = $("#queue-query").value.trim().toLowerCase();
  const filter = $("#queue-status").value;
  let shown = 0;
  for (const [index, item] of state.items.entries()) {
    const statusName = reviewState(item);
    if (query && !`${item.agent_name} ${item.preview} ${item.claim_id}`.toLowerCase().includes(query)) continue;
    if (filter !== "all" && !(filter === "open" ? statusName !== "complete" : statusName === filter)) continue;
    shown++;
    const button = node("button", "episode-nav" + (item.claim_id === state.activeId ? " active" : ""));
    button.type = "button";
    const num = node("span", "episode-number", String(index + 1).padStart(2, "0"));
    const info = node("span", "episode-info");
    info.append(node("strong", "", item.agent_name), node("small", "", item.created_at.slice(5, 16) + " UTC"));
    const status = item.total_units ? `${item.labeled_units}/${item.total_units} units labeled` : "Unreviewed";
    info.append(node("small", "tag" + (item.total_units ? "" : " empty"), status));
    button.append(num, info);
    button.addEventListener("click", () => openEpisode(item.claim_id));
    nav.append(button);
  }
  const complete = state.items.filter(x => x.total_units && x.labeled_units === x.total_units).length;
  $("#progress").textContent = `${complete}/${state.items.length} fully labeled`;
  $("#queue-summary").textContent = `${shown} of ${state.items.length} shown` + (state.source.queue_seed ? ` · seed ${state.source.queue_seed}` : state.source.mode === "development_review" ? " · excluded from held-out evaluation" : " · invented examples");
  if (!shown) nav.append(node("p", "empty-queue", "No episodes match these filters."));
  const index = state.items.findIndex(x => x.claim_id === state.activeId);
  $("#previous-episode").disabled = index <= 0;
  $("#next-episode").disabled = index < 0 || index >= state.items.length - 1;
  $("#next-open").disabled = !state.items.some(x => x.claim_id !== state.activeId && reviewState(x) !== "complete");
}

function nextOpen() {
  const index = state.items.findIndex(x => x.claim_id === state.activeId);
  for (let step = 1; step < state.items.length; step++) {
    const item = state.items[(index + step) % state.items.length];
    if (reviewState(item) !== "complete") return openEpisode(item.claim_id);
  }
}

function updateReadiness() {
  const units = getUnits();
  const unlabeled = units.filter(x => !x.status).length;
  const withoutRationale = units.filter(x => x.status && x.status !== "not_a_claim" && !x.notes).length;
  const withoutCite = units.filter(x => ["supported", "contradicted", "mixed"].includes(x.status) && !x.evidence_ids.length).length;
  const cues = [];
  if (unlabeled) cues.push(`${unlabeled} unit${unlabeled === 1 ? "" : "s"} unlabeled`);
  if (withoutCite) cues.push(`${withoutCite} decisive label${withoutCite === 1 ? "" : "s"} without a cited turn`);
  if (withoutRationale) cues.push(`${withoutRationale} label${withoutRationale === 1 ? "" : "s"} without a rationale`);
  $("#review-readiness").textContent = cues.length ? `Review cues: ${cues.join(" · ")}. You can still save a partial review.` : "All units labeled with the expected citation or rationale fields.";
}

function setActiveUnit(id) {
  state.activeUnit = id;
  for (const card of $$(".unit-card")) {
    card.classList.toggle("active", card.dataset.unitId === id);
    $("input[type=radio]", card).checked = card.dataset.unitId === id;
  }
}

function renderCitationLinks(card) {
  const links = $(".citation-links", card); links.replaceChildren();
  const ids = $(".id-input", card).value.split(/[,\s]+/).filter(Boolean);
  for (const [index, tid] of [...new Set(ids)].entries()) {
    const link = node("button", "subtle", `Open cited record ${index + 1}`);
    link.type = "button"; link.title = tid;
    link.addEventListener("click", () => showTurn(tid));
    links.append(link);
  }
}

function addUnit(unit = {}) {
  const id = unit.unit_id || `u${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const card = node("article", "unit-card");
  card.dataset.unitId = id;
  card.innerHTML = `<div class="unit-head"><input type="radio" name="active-unit" aria-label="Select active claim unit"><label>Claim unit</label><button type="button" class="remove-unit">Remove</button></div>
    <textarea class="unit-text" aria-label="Atomic claim text" placeholder="One independently checkable assertion"></textarea>
    <div class="form-grid"><label class="field"><span>Evidence status</span><select class="unit-status"><option value="">Unlabeled</option><option value="supported">Supported</option><option value="contradicted">Contradicted</option><option value="mixed">Mixed</option><option value="unresolved">Unresolved / insufficient evidence</option><option value="not_a_claim">Not a completion claim</option></select></label>
    <label class="field"><span>Confidence / uncertainty</span><select class="unit-confidence"><option value="">Unspecified</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low / uncertain</option></select></label>
    <label class="field full"><span>Cited turn IDs (comma separated)</span><input class="id-input" type="text" placeholder="Select a turn's Cite button or paste its ID"></label>
    <label class="field full"><span>Why? What evidence is missing or conflicting?</span><textarea class="notes" placeholder="Brief rationale; note missing screenshots or later corroboration"></textarea></label></div>`;
  $(".unit-text", card).value = unit.text || "";
  $(".unit-status", card).value = unit.status || "";
  $(".unit-confidence", card).value = unit.confidence || "";
  $(".id-input", card).value = (unit.evidence_ids || []).join(", ");
  $(".notes", card).value = unit.notes || "";
  card.append(node("div", "card-actions citation-links"));
  renderCitationLinks(card);
  $(".id-input", card).addEventListener("input", () => renderCitationLinks(card));
  card.addEventListener("input", event => {if (event.target.type !== "radio") markDirty();});
  card.addEventListener("change", event => {if (event.target.type !== "radio") markDirty();});
  $("input[type=radio]", card).addEventListener("change", () => setActiveUnit(id));
  $(".remove-unit", card).addEventListener("click", () => {
    if ($$(".unit-card").length === 1) return alert("Keep at least one unit; mark it 'Not a completion claim' if needed.");
    card.remove(); markDirty();
    if (state.activeUnit === id) setActiveUnit($(".unit-card").dataset.unitId);
  });
  $("#units").append(card);
  if (!state.activeUnit) setActiveUnit(id);
}

function getUnits() {
  return $$(".unit-card").map(card => ({
    unit_id: card.dataset.unitId,
    text: $(".unit-text", card).value.trim(),
    status: $(".unit-status", card).value,
    confidence: $(".unit-confidence", card).value,
    evidence_ids: $(".id-input", card).value.split(/[,\s]+/).map(x => x.trim()).filter(Boolean),
    notes: $(".notes", card).value.trim(),
  }));
}

function renderEvidence() {
  if (!state.episode) return;
  const phase = $("#lead-phase").value;
  const actor = $("#lead-actor").value;
  const route = $("#lead-route").value;
  const matching = state.episode.evidence.filter(e =>
    (phase === "all" || e.phase === phase) &&
    (actor === "all" || (actor === "claimant") === e.same_agent) &&
    (route === "all" || e.retrieved_by.some(x => x.startsWith(route)))
  );
  const list = $("#evidence-list"); list.replaceChildren();
  for (const e of matching) list.append(evidenceCard(e));
  if (!matching.length) list.append(node("p", "empty-queue", "No initial leads match. Adjust the filters or search more turns."));
  $("#evidence-count").textContent = `${matching.length} of ${state.episode.evidence.length} leads`;
}

function citeTurn(id) {
  const card = $$(".unit-card").find(x => x.dataset.unitId === state.activeUnit);
  if (!card) return alert("Select a claim unit first.");
  const input = $(".id-input", card);
  const ids = input.value.split(/[,\s]+/).filter(Boolean);
  if (!ids.includes(id)) ids.push(id);
  input.value = ids.join(", ");
  renderCitationLinks(card);
  markDirty();
  card.scrollIntoView({behavior: "smooth", block: "nearest"});
}

function evidenceCard(e) {
  const card = node("article", "evidence-card" + (e.phase === "after" ? " after" : "") + (!e.same_agent ? " other" : ""));
  const head = node("header");
  head.append(node("time", "", e.created_at + " UTC"), node("span", "record-id", e.turn_id));
  card.append(head);
  const pills = node("div", "pills");
  pills.append(node("span", "pill" + (e.phase === "after" ? " after" : ""), e.phase === "after" ? "After claim" : "Before claim"));
  pills.append(node("span", "pill" + (!e.same_agent ? " other" : ""), `${e.same_agent ? "Claimant" : "Other agent"} · ${e.actor_name || "Unknown"}`));
  if (e.screenshot_is_redacted) pills.append(node("span", "pill", "Screenshot redacted"));
  if (e.evidence_stage) pills.append(node("span", "pill", e.evidence_stage.replaceAll("_", " ")));
  if (Number.isFinite(e.record_offset_seconds)) pills.append(node("span", "pill", `Record time: ${e.record_offset_seconds >= 0 ? "+" : ""}${e.record_offset_seconds.toFixed(3)}s from claim`));
  card.append(pills);
  for (const [label, value, className] of [["Action", e.action_excerpt, ""], ["Tool output", e.output_excerpt, ""], ["Stderr / errors (inspect content)", e.error_excerpt, "stderr"]]) {
    if (!value || value === "{}") continue;
    card.append(node("div", "record-id", label), node("pre", className, value));
  }
  const source = state.source.mode === "synthetic_demo" ? "invented teaching record" : `pinned Parquet revision ${state.source.parquet_revision.slice(0, 12)}`;
  card.append(node("div", "record-id", `Session ${e.session_id} · ${e.source_shard} · ${source}`));
  const route = node("details", "route");
  route.append(node("summary", "record-id", "Why this turn was retrieved"),
               node("div", "record-id", e.retrieved_by.join(", ")));
  card.append(route);
  const actions = node("div", "card-actions");
  const cite = node("button", "", "Cite in selected claim"); cite.type = "button";
  cite.addEventListener("click", () => citeTurn(e.turn_id));
  const full = node("button", "", "Full record"); full.type = "button";
  full.addEventListener("click", () => showTurn(e.turn_id));
  actions.append(cite, full); card.append(actions);
  return card;
}

async function showTurn(id) {
  const request = ++state.turnRequest;
  const cid = state.activeId;
  try {
    const {turn} = await api(`/api/turn/${encodeURIComponent(id)}`);
    if (request !== state.turnRequest || cid !== state.activeId || state.loading) return;
    const body = $("#record-body"); body.replaceChildren();
    body.append(node("p", "record-id", `Turn ${turn.id} · Session ${turn.session_id} · ${turn.created_at} UTC · ${turn.source_shard}`));
    for (const [name, value] of [["Action", turn.agent_action], ["Tool output", turn.output], ["Stderr / errors (not a failure verdict)", turn.error]]) {
      if (value === null || value === undefined || value === "") continue;
      body.append(node("h3", "", name), node("pre", "", typeof value === "string" ? value : JSON.stringify(value, null, 2)));
    }
    body.append(node("p", "record-id", `screenshot_is_redacted=${turn.screenshot_is_redacted}; has_redaction_been_overruled=${turn.has_redaction_been_overruled}`));
    if (!$("#record-dialog").open) $("#record-dialog").showModal();
  } catch (error) { alert(error.message); }
}

function renderIntegrity(integrity, policy) {
  $("#review-provenance").textContent = integrity.message;
  $("#review-provenance").dataset.status = integrity.status;
  $("#assessment-policy").textContent = policy ? JSON.stringify(policy, null, 2) : "No review policy has been saved for this assessment.";
}

function renderSummary(summary) {
  $("#summary-attribution").textContent = summary.attribution;
  $("#summary-assertion").textContent = summary.assertion;
  $("#summary-note").textContent = summary.note;
  for (const group of ["before", "later"]) {
    const list = $("#summary-" + group); list.replaceChildren();
    for (const observation of summary[group]) {
      const item = node("div", "summary-observation");
      item.append(node("p", "", observation.text));
      const links = node("div", "summary-sources");
      for (const source of observation.sources) {
        const offset = source.record_offset_seconds;
        const text = `${source.actor_name} · ${offset > 0 ? "+" : ""}${offset.toFixed(3)}s · ${source.phase === "after" ? "after claim" : "before / at claim"}`;
        const link = node("button", "summary-source", text);
        link.type = "button"; link.dataset.turnId = source.turn_id;
        link.title = `Open source ${source.turn_id} · ${source.created_at} UTC`;
        link.addEventListener("click", () => showTurn(source.turn_id));
        links.append(link);
      }
      item.append(links); list.append(item);
    }
    if (!summary[group].length) list.append(node("p", "summary-empty", "No source selected for this part of the overview; this does not establish absence."));
  }
  const unresolved = $("#summary-unresolved"); unresolved.replaceChildren();
  for (const text of summary.unresolved) unresolved.append(node("li", "", text));
  $("#summary-save-state").textContent = state.dirty ? "Unsaved edits are not reflected in this overview." : "";
}

function renderEpisode(episode, review, summary, integrity) {
  state.episode = episode; state.activeUnit = null; state.dirty = false;
  $("#loading").hidden = true; $("#episode-view").hidden = false;
  const index = state.items.findIndex(x => x.claim_id === episode.claim_id);
  $("#position").textContent = `Episode ${index + 1} of ${state.items.length}`;
  $("#episode-heading").textContent = episode.case_title || episode.agent_name + " · completion-claim candidate";
  $("#episode-meta").textContent = `${episode.agent_name} · ${episode.created_at} UTC · message ${episode.claim_id}`;
  $("#original-message").textContent = episode.message;
  const demo = state.source.mode === "synthetic_demo";
  $("#message-description").textContent = demo ? "Invented agent message for demonstration" : "Exact agent chat text from the pinned export";
  $("#provenance").textContent = demo ? "All messages and actions here are invented. Practice annotations are saved separately and never count as research findings." : `AI Digest / AI Village · main revision ${state.source.main_revision} · converted Parquet revision ${state.source.parquet_revision}. ${state.source.source_card}. This is a partial converted export, without screenshots; missing evidence does not establish failure.`;
  $("#episode-guidance").textContent = episode.demo_lesson || (state.source.mode === "development_review" ? "These source records were selected during AI-assisted development. Check each assertion independently; this case cannot count toward held-out results." : "Inspect the recorded action and its result. Separate repository state, deployment state, and claims about what users could see.");
  const before = episode.evidence.filter(e => e.phase === "before").length;
  const after = episode.evidence.length - before;
  const other = episode.evidence.filter(e => !e.same_agent).length;
  $("#timeline-summary").textContent = `${before} leads before → claim at ${episode.created_at.slice(11, 19)} UTC → ${after} after · ${other} from other agents. Timing alone does not prove transmission.`;
  const baseline = $("#baseline-sessions"); baseline.replaceChildren();
  for (const s of episode.baseline_top3_sessions) baseline.append(node("div", "session", `${s.created_at} UTC · score ${s.score} · ${s.short_goal || "(no short goal)"} · session ${s.session_id}`));
  if (!episode.baseline_top3_sessions.length) baseline.append(node("p", "", "No session-goal ranking is included in this example."));
  const units = $("#units"); units.replaceChildren();
  for (const unit of (review ? review.units : episode.proposed_units)) addUnit(unit);
  updateReadiness();
  $("#unit-description").textContent = state.source.mode === "ai_assisted_review" ? "AI-assisted judgments, with qualitative confidence and cited records. Editable; changes remain separate from independent human labels." : "Suggested text spans are editable. Split or remove them as needed.";
  $("#save-status").textContent = review ? `Last saved ${review.reviewed_at_utc}` : "No annotations saved yet.";
  renderSummary(summary);
  renderIntegrity(integrity, review?.assessment_policy);
  renderEvidence();
  $("#search-results").replaceChildren(); $("#search-note").textContent = "";
  $("#search-query").value = "";
}

async function openEpisode(id) {
  if (state.saving) { $("#save-status").textContent = "Saving… wait before changing episodes."; return; }
  if (state.dirty && !confirm("Discard unsaved edits for this episode?")) return;
  const request = ++state.episodeRequest;
  state.searchRequest++; state.turnRequest++; state.loading = true;
  $("#episode-view").inert = true;
  try {
    const {episode, review, revision, summary, integrity} = await api(`/api/episode/${encodeURIComponent(id)}`);
    if (request !== state.episodeRequest) return;
    state.activeId = id;
    state.revision = revision;
    renderEpisode(episode, review, summary, integrity);
    updateNavigation();
    const url = new URL(window.location.href);
    url.searchParams.set("episode", id);
    window.history.replaceState(null, "", url);
    $("#workspace").scrollTo(0, 0);
  } catch (error) { if (request === state.episodeRequest) alert(error.message); }
  finally { if (request === state.episodeRequest) { state.loading = false; $("#episode-view").inert = false; } }
}

async function saveReview() {
  if (state.saving || state.loading) return;
  const cid = state.activeId, editVersion = state.editVersion;
  try {
    const units = getUnits();
    if (units.some(x => !x.text)) return alert("Each unit needs claim text. Remove empty units before saving.");
    state.saving = true;
    $("#save-review").disabled = true;
    $("#save-status").textContent = "Saving…";
    const result = await api(`/api/review/${encodeURIComponent(cid)}`, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({claim_id: cid, units, base_revision: state.revision}),
    });
    state.revision = result.revision;
    state.dirty = state.editVersion !== editVersion;
    $("#save-status").textContent = state.dirty ? "Saved earlier edits; newer changes still unsaved." : `Saved ${result.reviewed_at_utc}`;
    const item = state.items.find(x => x.claim_id === cid);
    item.total_units = units.length; item.labeled_units = units.filter(x => x.status).length;
    updateNavigation();
    updateReadiness();
    renderSummary(result.summary);
    renderIntegrity(result.integrity, result.assessment_policy);
  } catch (error) { $("#save-status").textContent = error.message; }
  finally { state.saving = false; $("#save-review").disabled = false; }
}

async function searchTurns(event) {
  event.preventDefault();
  if (state.loading) return;
  const request = ++state.searchRequest, cid = state.activeId;
  const note = $("#search-note"); note.textContent = "Searching local turn records…";
  const params = new URLSearchParams({episode_id: state.activeId, q: $("#search-query").value,
    scope: $("#search-scope").value, phase: $("#search-phase").value});
  try {
    const result = await api("/api/search?" + params);
    if (request !== state.searchRequest || cid !== state.activeId) return;
    const list = $("#search-results"); list.replaceChildren();
    for (const e of result.results) list.append(evidenceCard(e));
    note.textContent = `${result.results.length} ranked leads from ${result.candidate_turns} eligible turns. Scores indicate text similarity only.`;
  } catch (error) { if (request === state.searchRequest && cid === state.activeId) note.textContent = error.message; }
}

async function init() {
  try {
    state.source = await api("/api/episodes");
    state.items = state.source.items;
    const demo = state.source.mode === "synthetic_demo";
    const development = state.source.mode === "development_review";
    const ai = state.source.mode === "ai_assisted_review";
    $("#data-mode").textContent = demo ? "Synthetic demo · no dataset required" : development ? "Development cases · AI-assisted reconstruction" : ai ? "AI-assisted review · not independent validation" : "Research pilot · AI Village partial export";
    $("#data-mode").classList.toggle("demo", demo);
    $("#queue-heading").textContent = demo ? "Practice cases" : development ? "Two development cases" : ai ? "25 AI-reviewed episodes" : "Frozen review queue";
    $("#export-reviews").textContent = demo ? "Export practice labels" : development ? "Export case annotations" : ai ? "Export AI assessments" : "Export human labels";
    const citedRoute = node("option", "", "Saved citations"); citedRoute.value = "review citation";
    $("#lead-route").append(citedRoute);
    updateNavigation();
    $("#queue-query").addEventListener("input", updateNavigation);
    $("#queue-status").addEventListener("change", updateNavigation);
    for (const id of ["#lead-phase", "#lead-actor", "#lead-route"]) $(id).addEventListener("change", renderEvidence);
    $("#previous-episode").addEventListener("click", () => openEpisode(state.items[state.items.findIndex(x => x.claim_id === state.activeId) - 1].claim_id));
    $("#next-episode").addEventListener("click", () => openEpisode(state.items[state.items.findIndex(x => x.claim_id === state.activeId) + 1].claim_id));
    $("#next-open").addEventListener("click", nextOpen);
    $("#add-unit").addEventListener("click", () => { addUnit(); markDirty(); });
    $("#save-review").addEventListener("click", saveReview);
    $("#search-form").addEventListener("submit", searchTurns);
    $("#search-selected-unit").addEventListener("click", () => {
      const card = $$(".unit-card").find(x => x.dataset.unitId === state.activeUnit);
      if (!card) return;
      $("#search-query").value = $(".unit-text", card).value.slice(0, 500);
      $("#search-form").requestSubmit();
    });
    $("#close-dialog").addEventListener("click", () => $("#record-dialog").close());
    const requested = new URLSearchParams(window.location.search).get("episode");
    const initial = state.items.find(x => x.claim_id === requested) || state.items[0];
    if (initial) await openEpisode(initial.claim_id);
  } catch (error) { $("#loading").textContent = `Could not load review queue: ${error.message}`; }
}

window.addEventListener("beforeunload", event => {if (state.dirty || state.saving) {event.preventDefault(); event.returnValue = "";}});
init();
