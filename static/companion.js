(() => {
"use strict";
let root=null,busy=false,brief="";
const $=s=>(root||document).querySelector(s);
async function api(path,opts={}) {
 const headers=Object.assign({},opts.body?{"Content-Type":"application/json"}:{},opts.headers||{});
 const r=await fetch(path,Object.assign({},opts,{headers,credentials:"same-origin"}));
 let data={};try{data=await r.json()}catch(_){}
 if(!r.ok)throw new Error(data.detail||data.message||("Request failed ("+r.status+")"));
 return data;
}
function say(text,role) {
 const row=document.createElement("div");row.className="mitra-message "+(role==="user"?"is-user":"is-assistant");
 const label=document.createElement("span");label.className="mitra-message-label";label.textContent=role==="user"?"You":"Mitra";
 const bubble=document.createElement("p");bubble.className="mitra-message-bubble";bubble.textContent=String(text||"");
 row.append(label,bubble);$("#mitra-chat-messages").appendChild(row);
 $("#mitra-chat-messages").scrollTop=$("#mitra-chat-messages").scrollHeight;
}
function setBusy(v){busy=v;$("#mitra-chat-input").disabled=v;$("#mitra-chat-send").disabled=v;$("#mitra-chat-send").textContent=v?"…":"Send";}
async function send(text){
 text=String(text||"").trim();if(!text||busy)return;
 say(text,"user");$("#mitra-chat-input").value="";setBusy(true);
 try{const r=await api("/api/companion/chat",{method:"POST",body:JSON.stringify({message:text})});say(r.reply,"assistant");}
 catch(e){say("I couldn't load that response: "+e.message+". Please try again.","assistant");}
 finally{setBusy(false);$("#mitra-chat-input").focus();}
}
function reportText(d,kind){
 const visit=kind==="visit",lines=["MITRACARE — "+(visit?"CLINICIAN VISIT BRIEF":"FAMILY CARE HANDOVER"),
 "Care profile: "+d.profile,"Prepared: "+d.prepared_at_local+" ("+d.timezone+")","Prepared by: "+d.prepared_by,"",d.data_note,""];
 if(visit){
  lines.push("ACTIVE MEDICATION SCHEDULES ENTERED IN MITRACARE");
  if(!d.medications.length)lines.push("No active schedules are recorded.");
  d.medications.forEach((m,i)=>{lines.push((i+1)+". "+m.name+(m.strength?" · "+m.strength:""));
   lines.push("   Route: "+(m.route||"Not entered")+" | Times: "+(m.times||[]).join(", "));
   if(m.instructions_entered)lines.push("   Instructions entered: "+m.instructions_entered);
   if(m.prescriber_entered)lines.push("   Prescriber entered: "+m.prescriber_entered);
   lines.push("   Dates: "+(m.start_date||"Not entered")+(m.end_date?" to "+m.end_date:" onwards"));});
  lines.push("","RECORDED CHECK-INS — LAST 14 DAYS");const c=d.checkin_counts_14d||{};
  lines.push("Recorded as taken: "+(c.taken||0)+" | skipped: "+(c.skipped||0)+" | missed: "+(c.missed||0));
  if(!d.checkins.length)lines.push("No check-ins recorded in this window.");
  d.checkins.forEach(x=>lines.push("• "+x.scheduled_local+" — "+x.medication+" — "+x.status+" — recorded by "+x.recorded_by));
  lines.push("","APPOINTMENTS");if(!d.appointments.length)lines.push("No appointment in this date window.");
  d.appointments.forEach(x=>lines.push("• "+x.local_time+" — "+x.clinician+(x.location?" — "+x.location:"")));
  lines.push("","QUESTIONS TO DISCUSS WITH THE CLINICIAN");d.visit_questions.forEach((x,i)=>lines.push((i+1)+". "+x));
 } else {
  lines.push("OPEN AND RECENTLY COMPLETED FOLLOW-UPS");if(!d.tasks.length)lines.push("No open or recently completed follow-ups are recorded.");
  d.tasks.forEach(x=>{lines.push("• ["+x.status.toUpperCase()+"] "+x.title+" — owner: "+x.assigned_to+" — due: "+x.due_local);
   if(x.description)lines.push("  "+x.description);if(x.completed_by!=="Not recorded")lines.push("  Completed by: "+x.completed_by+(x.completed_at?" at "+x.completed_at:""));});
  lines.push("","UPCOMING APPOINTMENTS");const upcoming=d.appointments.filter(x=>new Date(x.starts_at)>=new Date());
  if(!upcoming.length)lines.push("No upcoming appointments in this date window.");
  upcoming.forEach(x=>lines.push("• "+x.local_time+" — "+x.clinician+(x.location?" — "+x.location:"")));
  lines.push("","NEXT SCHEDULED CHECK-INS — AS ENTERED");if(!d.upcoming_doses.length)lines.push("No scheduled check-ins in the next 7 days.");
  d.upcoming_doses.forEach(x=>lines.push("• "+x.scheduled_local+" — "+x.medication));
  lines.push("","RECENT CARE-CIRCLE ACTIVITY");if(!d.recent_activity.length)lines.push("No activity entries are recorded.");
  d.recent_activity.forEach(x=>lines.push("• "+x.at+" — "+x.actor+": "+x.detail));
  lines.push("","ACTIVE CARE-CIRCLE MEMBERS");d.care_circle.forEach(x=>lines.push("• "+x.name+" — "+x.role));
 }
 lines.push("","Privacy: this contains care-related information. Share only with the patient's permission.",
 "MitraCare is a coordination tool, not an emergency service or source of medical advice.");
 return lines.join("\n");
}
async function makeBrief(kind){
 if(busy)return;
 if(!$("#mitra-brief-consent").checked){say("Confirm that the patient has permitted this brief to be prepared and shared.","assistant");return;}
 setBusy(true);
 try{
  const d=await api("/api/companion/brief",{method:"POST",body:JSON.stringify({kind,consent:true})});
  brief=reportText(d,kind);$("#mitra-brief-title").textContent=kind==="visit"?"Clinician visit brief":"Family care handover";
  $("#mitra-brief-preview").textContent=brief;$("#mitra-brief-card").hidden=false;$("#mitra-brief-card").dataset.kind=kind;
  say("Brief prepared. Review every entry before sharing. You can copy, download or print it here.","assistant");
 }catch(e){say("I couldn't prepare the brief: "+e.message,"assistant");}
 finally{setBusy(false);}
}
async function copyBrief(){if(!brief)return;try{await navigator.clipboard.writeText(brief);say("Brief copied. Share only with the patient's permission.","assistant");}catch(_){say("Clipboard access was blocked. Use Download .txt instead.","assistant");}}
function downloadBrief(){
 if(!brief)return;const kind=$("#mitra-brief-card").dataset.kind||"care-brief";
 const url=URL.createObjectURL(new Blob([brief],{type:"text/plain;charset=utf-8"}));
 const a=document.createElement("a");a.href=url;a.download="mitracare-"+kind+"-"+new Date().toISOString().slice(0,10)+".txt";
 document.body.appendChild(a);a.click();a.remove();window.setTimeout(()=>URL.revokeObjectURL(url),1500);
}
function printBrief(){
 if(!brief)return;const sheet=document.createElement("main");sheet.id="mitra-companion-print-sheet";
 const h=document.createElement("h1");h.textContent="MitraCare care brief";
 const pre=document.createElement("pre");pre.textContent=brief;sheet.append(h,pre);document.body.appendChild(sheet);
 const clean=()=>{if(sheet.isConnected)sheet.remove();};window.addEventListener("afterprint",clean,{once:true});
 window.print();window.setTimeout(clean,30000);
}
function mount(){
 const logged=!!document.querySelector(".app-shell"),old=document.getElementById("mitra-companion");
 if(!logged){if(old)old.remove();root=null;brief="";return;}
 if(old){root=old;return;}
 root=document.createElement("div");root.id="mitra-companion";
 root.innerHTML=
 '<button id="mitra-chat-trigger" class="mitra-chat-trigger" type="button" aria-label="Open Mitra care companion" aria-expanded="false"><span class="mitra-chat-orb" aria-hidden="true">m</span><span>Ask Mitra</span></button>'+
 '<section id="mitra-chat-panel" class="mitra-chat-panel" role="dialog" aria-label="Mitra care companion" hidden>'+
 '<header class="mitra-chat-header"><div><span class="mitra-chat-eyebrow">YOUR CARE COORDINATION GUIDE</span><strong>Mitra Companion</strong><small>Private local help · no API key required</small></div><button id="mitra-chat-close" class="mitra-chat-close" type="button" aria-label="Close companion">×</button></header>'+
 '<div class="mitra-chat-privacy">This uses records available to your signed-in role. Chat text is not saved or sent to an AI provider. Not a doctor or emergency service.</div>'+
 '<div id="mitra-chat-messages" class="mitra-chat-messages" aria-live="polite"></div>'+
 '<div class="mitra-chat-shortcuts"><button type="button" data-prompt="What needs attention today?">Today’s priorities</button><button type="button" data-prompt="Show open follow-up tasks.">Open tasks</button><button type="button" data-prompt="When is the next appointment?">Next visit</button><button type="button" data-prompt="Who is in the care circle?">Care circle</button></div>'+
 '<div class="mitra-chat-brief-actions"><button type="button" data-brief="visit">Visit brief</button><button type="button" data-brief="handover">Family handover</button></div>'+
 '<label class="mitra-brief-consent"><input id="mitra-brief-consent" type="checkbox"><span>I confirm the patient has permitted this brief to be prepared and shared.</span></label>'+
 '<section id="mitra-brief-card" class="mitra-brief-card" hidden><div class="mitra-brief-head"><strong id="mitra-brief-title">Care brief</strong><span>Review before sharing</span></div><pre id="mitra-brief-preview"></pre><div class="mitra-brief-actions"><button type="button" data-brief-action="copy">Copy</button><button type="button" data-brief-action="download">Download .txt</button><button type="button" data-brief-action="print">Print</button></div></section>'+
 '<form id="mitra-chat-form" class="mitra-chat-form"><label class="visually-hidden" for="mitra-chat-input">Ask a care-coordination question</label><input id="mitra-chat-input" maxlength="600" autocomplete="off" placeholder="Ask about tasks, visits or reminders…" required><button id="mitra-chat-send" type="submit">Send</button></form>'+
 '<p class="mitra-chat-foot">For medicine decisions or symptoms, contact the clinician or pharmacist. For emergencies, contact local emergency services.</p></section>';
 document.body.appendChild(root);
 say("Hello! I’m Mitra, your local care-coordination companion. I can summarise tasks, appointments and care-circle roles, and prepare visit or family handover briefs. I work without an AI key and do not diagnose or make medication decisions.","assistant");
 root.addEventListener("click",e=>{
  const b=e.target.closest("button");if(!b||!root.contains(b))return;
  if(b.id==="mitra-chat-trigger"){$("#mitra-chat-panel").hidden=false;b.setAttribute("aria-expanded","true");$("#mitra-chat-input").focus();}
  else if(b.id==="mitra-chat-close"){$("#mitra-chat-panel").hidden=true;$("#mitra-chat-trigger").setAttribute("aria-expanded","false");$("#mitra-chat-trigger").focus();}
  else if(b.dataset.prompt)send(b.dataset.prompt);else if(b.dataset.brief)makeBrief(b.dataset.brief);
  else if(b.dataset.briefAction==="copy")copyBrief();else if(b.dataset.briefAction==="download")downloadBrief();
  else if(b.dataset.briefAction==="print")printBrief();
 });
 $("#mitra-chat-form").addEventListener("submit",e=>{e.preventDefault();send($("#mitra-chat-input").value);});
 document.addEventListener("keydown",e=>{if(e.key==="Escape"&&root&&!$("#mitra-chat-panel").hidden){$("#mitra-chat-panel").hidden=true;$("#mitra-chat-trigger").setAttribute("aria-expanded","false");}});
}
const observer=new MutationObserver(mount);
function start(){mount();const app=document.getElementById("app");if(app)observer.observe(app,{childList:true,subtree:true});}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start,{once:true});else start();
})();