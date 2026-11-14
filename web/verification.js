"use strict";
const $ = s => document.querySelector(s);
let report, active;
const labels = {verified:"Verified contract", stale:"Stale evidence", scope_mismatch:"Wrong policy or scope", failed:"Check failed", changed_during_check:"Changed during execution", missing:"Missing receipt", later:"Later evidence", timeout:"Check timed out", unresolved:"Unresolved", workspace_mismatch:"Different workspace"};
function el(tag, text, className="") { const e=document.createElement(tag); e.textContent=text; e.className=className; return e; }
function navigation() {
  const list=$("#case-list"); list.replaceChildren(); let shown=0;
  for(const [i,c] of report.cases.entries()) {
    if($("#repo-filter").value!=="all" && c.repository!==$("#repo-filter").value) continue;
    if($("#status-filter").value!=="all" && c.result.status!==$("#status-filter").value) continue;
    shown++;
    const b=el("button","","episode-nav"+(active===c.id?" active":"")); b.type="button";
    if(active===c.id) b.setAttribute("aria-current","true");
    const info=el("span","","episode-info");
    info.append(el("strong",c.scenario.replaceAll("_"," ")),el("small",c.repository),el("small",labels[c.result.status]||c.result.status,"tag"));
    b.append(el("span",String(i+1).padStart(2,"0"),"episode-number"),info); b.addEventListener("click",()=>open(c.id)); list.append(b);
  }
  $("#queue-summary").textContent=`${shown} of ${report.cases.length} cases · host captures`;
  if(!shown) list.append(el("p","No matching cases.","empty-queue"));
}
function open(id) {
  const c=report.cases.find(x=>x.id===id); if(!c) return;
  active=id; navigation(); history.replaceState(null,"",`?case=${encodeURIComponent(id)}`);
  $("#loading").hidden=true; $("#case-view").hidden=false;
  $("#repo-name").textContent=c.repository; $("#case-kind").textContent=c.kind;
  $("#case-heading").textContent=c.scenario.replaceAll("_"," ").replace(/^./,x=>x.toUpperCase());
  const repo=report.repositories.find(r=>r.id===c.repository);
  $("#revision").textContent=`Pinned upstream revision ${repo?.revision||"unspecified"}`;
  $("#case-note").textContent=c.note;
  $("#verdict").dataset.status=c.result.status;
  $("#verdict-label").textContent=labels[c.result.status]||c.result.status;
  $("#verdict-reason").textContent=c.result.reason;
  $("#observation-time").textContent=`Observed ${c.result.observed_at} · captured snapshot, not live workspace state`;
  $("#required-command").textContent=[c.policy.command[0].split(/[\\/]/).pop(),...c.policy.command.slice(1)].join(" ");
  $("#required-command").title=c.policy.command.join(" "); $("#required-id").textContent=c.policy.check_id;
  $("#scope-roots").replaceChildren(...c.policy.scope.map(p=>el("code",p)));
  $("#excluded").textContent=`Explicit exclusions: ${c.policy.exclude.join(", ")||"none"}. Git metadata is not part of the content scope.`;
  $("#changes-wrap").hidden=!c.result.changed_paths.length;
  $("#changed-paths").replaceChildren(...c.result.changed_paths.map(p=>el("li",p)));
  const r=c.receipt, ex=r?.execution;
  $("#execution-status").textContent=ex?`${ex.timed_out?"Timed out · ":""}Exit ${ex.exit_code??"unknown"} · ${ex.duration_seconds}s`:"No execution receipt supplied";
  $("#execution-time").textContent=r?`${r.started_at} → ${r.finished_at}`:"A transcript claim cannot stand in for a receipt.";
  $("#captured-command").textContent=r?[r.policy.command[0].split(/[\\/]/).pop(),...r.policy.command.slice(1)].join(" "):"No captured command";
  $("#captured-command").title=r?r.policy.command.join(" "):"";
  $("#captured-scope").textContent=r?`Receipt scope: ${r.policy.scope.join(", ")}`:"No captured scope";
  $("#output").textContent=ex?[ex.stdout.excerpt,ex.stderr.excerpt].filter(Boolean).join("\n")||"No output recorded":"No captured output";
  const hashes=$("#hashes"); hashes.replaceChildren();
  for(const [label,value] of [["Required policy",c.result.policy_sha256],["Receipt policy",r?.policy_sha256],["Before check",r?.before.sha256],["After check",r?.after.sha256],["Observed scope",c.observation.snapshot.sha256]]) {
    hashes.append(el("dt",label),el("dd",value||"absent"));
  }
  $("#baseline").textContent=c.baseline_rerun?`Comparison execution: exit ${c.baseline_rerun.execution.exit_code}. Command: ${c.baseline_rerun.policy.command.join(" ")}`:"No additional baseline execution recorded for this case.";
  $("#claim-wrap").hidden=!c.goose_claim;
  $("#claim-text").textContent=c.goose_claim?.text||"";
  $("#claim-boundary").textContent=c.goose_claim?`Source message ${c.goose_claim.message_id} · session SHA-256 ${c.goose_claim.session_sha256}. Observation occurred after the session; it is not backdated to the message.`:"";
  $("#raw-records").textContent=JSON.stringify({policy:c.policy,receipt:c.receipt,observation:c.observation,result:c.result},null,2);
  $("#workspace").scrollTo({top:0,behavior:"instant"});
}
async function start() {
  try {
    const response=await fetch("/api/verification"); const data=await response.json(); if(!response.ok) throw new Error(data.error||"Unable to load report"); report=data;
    $("#counts").textContent=`${report.matching_cases}/${report.replayed_cases} expected outcomes replayed`;
    for(const r of report.repositories) $("#repo-filter").append(new Option(r.id,r.id));
    $("#report-limits").replaceChildren(...report.limits.map(t=>el("li",t)));
    for(const id of ["#repo-filter","#status-filter"]) $(id).addEventListener("change",navigation);
    const requested=new URLSearchParams(location.search).get("case");
    open(report.cases.some(c=>c.id===requested)?requested:report.cases.find(c=>c.result.status==="stale")?.id||report.cases[0].id);
  } catch(error) { $("#loading").textContent=error.message; }
}
start();
