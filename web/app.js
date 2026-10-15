'use strict';
let boot, currentPage='overview';
const state={
  draft:null,name:'',description:'',owner:'',reviewer:'',note:'',parentId:null,classificationId:null
}
;
const $=id=>document.getElementById(id);
function el(tag,attrs={
}
,...children){
  const n=document.createElement(tag);
  for(const [k,v] of Object.entries(attrs)){
    if(k==='class')n.className=v;
    else if(k==='on')for(const [event,fn]of Object.entries(v))n.addEventListener(event,fn);
    else if(k==='checked')n.checked=v;
    else if(k==='value')n.value=v;
    else n.setAttribute(k,v);
  }
  for(const child of children.flat()){
    if(child!==null&&child!==undefined)n.append(child instanceof Node?child:document.createTextNode(String(child)));
  }
  return n;
}
function notice(message,error=false){
  $('notice').textContent=message;
  $('notice').className=error?'error':'';
}
async function api(path,body){
  const options=body?{
    method:'POST',headers:{
      'Content-Type':'application/json','X-Workspace-Token':boot.token
    }
    ,body:JSON.stringify(body)
  }
  :{
  }
  ;
  const response=await fetch(path,options);
  let data;
  try{
    data=await response.json();
  }
  catch{
    throw Error('The workspace returned an unreadable response.');
  }
  if(!response.ok){
    throw Error(typeof data.detail==='string'?data.detail:'Check the submitted fields and try again.');
  }
  return data;
}
function actionClass(outcome){
  return outcome==='Do not proceed'?'stop':outcome==='Review required'?'review':outcome==='Clarification required'?'unknown':'';
}
function badge(outcome){
  return el('span',{
    class:'badge '+actionClass(outcome)
  }
  ,outcome);
}
function button(label,fn,primary=false){
  return el('button',{
    type:'button',class:primary?'primary':'secondary',on:{
      click:fn
    }
  }
  ,label);
}
function heading(title,description){
  return el('div',{
    class:'page-title'
  }
  ,el('h1',{
  }
  ,title),el('p',{
    class:'lead'
  }
  ,description));
}
function panel(...children){
  return el('div',{
    class:'panel'
  }
  ,...children);
}
function blankCase(){
  const c={
    forms:[],approval_status:boot.unknown
  }
  ;
  boot.dimensions.forEach(d=>c[d.id]=boot.unknown);
  return c;
}
function show(page){
  currentPage=page;
  document.querySelectorAll('.page').forEach(n=>n.hidden=n.id!==page);
  document.querySelectorAll('nav button').forEach(n=>{
    if(n.dataset.page===page)n.setAttribute('aria-current','page');
    else n.removeAttribute('aria-current');
  }
  );
  $('breadcrumb').textContent={overview:'Overview',assess:'Assess a use case',register:'Register',framework:'Framework',validation:'Test results'}[page]||page;
  notice('');
  if(page==='overview')renderOverview();
  if(page==='assess')renderAssess();
  if(page==='register')renderRegister().catch(e=>notice(e.message,true));
  if(page==='framework')renderFramework();
  if(page==='validation')renderValidation();
  window.scrollTo({
    top:0,behavior:'auto'
  }
  );
}
function newAssessment(example=null){
  state.draft=example?structuredClone(example.case):blankCase();
  state.name=example?example.name:'';
  state.description=example?example.description:'';
  state.parentId=null;
  state.classificationId=null;
  state.note='';
  state.owner='';
  state.reviewer='';
  show('assess');
}
const CHANGE_FIELDS=['tool_access','information_involved','role_of_output','banking_process','task_expertise','approval_status'];
function fieldLabel(id){
  if(id==='approval_status')return 'Approval of this specific use';
  const d=boot.dimensions.find(x=>x.id===id);
  return d?d.name:id;
}
function sentence(text){
  const t=text.replace(/^Synthetic example: /,'');
  return t.charAt(0).toUpperCase()+t.slice(1);
}
function pairCard(side){
  return el('button',{class:'pair-card',type:'button',on:{click:()=>newAssessment(side)}},
    el('strong',{},side.name),
    el('span',{class:'pair-desc'},sentence(side.description)),
    badge(side.assessment.outcome));
}
function pairSlide(pair,index,total){
  const changes=CHANGE_FIELDS.filter(f=>pair.a.case[f]!==pair.b.case[f]);
  return el('div',{class:'pair-slide',role:'group','aria-roledescription':'slide','aria-label':(index+1)+' of '+total},
    el('h3',{},pair.title),
    pairCard(pair.a),
    el('div',{class:'pair-change'},changes.map(f=>el('p',{},el('strong',{},fieldLabel(f)),' changes from ',pair.a.case[f],' to ',pair.b.case[f],'.'))),
    pairCard(pair.b));
}
function pairCarousel(){
  const pairs=boot.lookalikes,total=pairs.length;
  const track=el('div',{class:'pair-track',tabindex:'0','aria-label':'Examples that look alike but get different outcomes'},pairs.map((p,i)=>pairSlide(p,i,total)));
  const prev=el('button',{type:'button',class:'pair-arrow','aria-label':'Previous example'},'\u2039');
  const next=el('button',{type:'button',class:'pair-arrow','aria-label':'Next example'},'\u203a');
  const counter=el('span',{class:'pair-count','aria-live':'polite'});
  const dots=pairs.map((p,i)=>el('button',{type:'button',class:'pair-dot','aria-label':'Show example '+(i+1)}));
  const reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const current=()=>Math.max(0,Math.min(total-1,Math.round(track.scrollLeft/Math.max(1,track.clientWidth))));
  const go=i=>track.scrollTo({left:Math.max(0,Math.min(total-1,i))*track.clientWidth,behavior:reduce?'auto':'smooth'});
  function update(){
    const i=current();
    dots.forEach((d,k)=>{if(k===i)d.setAttribute('aria-current','true');else d.removeAttribute('aria-current');});
    counter.textContent=(i+1)+' of '+total;
    prev.disabled=i===0;
    next.disabled=i===total-1;
  }
  let timer;
  track.addEventListener('scroll',()=>{clearTimeout(timer);timer=setTimeout(update,50);});
  track.addEventListener('keydown',e=>{
    if(e.key==='ArrowRight'){e.preventDefault();go(current()+1);}
    if(e.key==='ArrowLeft'){e.preventDefault();go(current()-1);}
  });
  prev.addEventListener('click',()=>go(current()-1));
  next.addEventListener('click',()=>go(current()+1));
  dots.forEach((d,i)=>d.addEventListener('click',()=>go(i)));
  update();
  return el('div',{class:'pairs'},track,
    el('div',{class:'pair-controls'},prev,el('div',{class:'pair-dots'},dots),next,counter),
    el('p',{class:'pair-note'},'Made-up examples that show how the sample policy reacts. Select a card to open it.'));
}
function renderOverview(){
  const root=$('overview');
  root.replaceChildren();
  root.append(el('div',{class:'hero'},
    el('div',{class:'hero-copy'},
      el('h1',{},'Govern the use,',el('br'),'not just the tool.'),
      el('p',{class:'lead'},'Describe what an employee did with an AI tool. See which risks and controls apply, and keep a record of your review.'),
      el('div',{class:'actions'},button('Assess a use case',()=>newAssessment(),true),button('Explore the framework',()=>show('framework')))),
    pairCarousel()));
  root.append(el('div',{class:'section-head'},el('h2',{},'Or start from an example'),el('p',{},'All examples are made up. They are not saved until you save them.')));
  const cards=el('div',{class:'cards'});
  boot.examples.forEach((e,i)=>cards.append(el('button',{class:'sample',type:'button',on:{click:()=>newAssessment(e)}},
    el('span',{class:'small-label'},'Example '+(i+1)),el('h3',{},e.name),badge(e.assessment.outcome))));
  root.append(cards);
}
function field(label,input,hint=''){
  const wrapper=el('div',{
    class:'field'
  }
  ,el('label',{
    for:input.id
  }
  ,label),input);
  if(hint)wrapper.append(el('div',{
    class:'hint'
  }
  ,hint));
  return wrapper;
}
function input(id,value='',max=160){
  return el('input',{
    id,value,maxlength:max
  }
  );
}
function choiceGroup(id,title,values,value,tip=''){
  const group=el('fieldset',{class:'choice-group',id,title:tip},el('legend',{},title));
  const row=el('div',{class:'choices'});
  values.forEach(v=>{
    const unknown=v===boot.unknown;
    const input=el('input',{type:'radio',name:id,value:v,checked:(value||boot.unknown)===v});
    row.append(el('label',{class:'choice'+(unknown?' choice-unknown':'')},input,el('span',{},unknown?'Not sure yet':v)));
  });
  group.append(row);
  return group;
}
function choiceValue(id){
  const c=document.querySelector('#'+id+' input:checked');
  return c?c.value:boot.unknown;
}
function readForm(){
  if(!$('case-name'))return;
  state.name=$('case-name').value;
  state.description=$('description').value;
  state.owner=$('owner').value;
  state.reviewer=$('reviewer').value;
  state.note=$('review-note').value;
  state.draft.forms=boot.forms.filter(f=>$('form-'+f.id).checked).map(f=>f.id);
  boot.dimensions.forEach(d=>state.draft[d.id]=choiceValue(d.id));
  state.draft.approval_status=choiceValue('approval-status');
}
function updateSaveState(){
  const save=$('save-record');
  if(!save)return;
  readForm();
  const missing=[];
  if(!state.name.trim())missing.push('a name');
  if(!state.owner.trim())missing.push('an owner');
  if(!state.reviewer.trim())missing.push('a reviewer');
  if(!$('confirm-review').checked)missing.push('your confirmation');
  save.disabled=missing.length>0;
  $('save-hint').textContent=missing.length?'To save, add '+missing.join(', ')+'.':'';
}
let assessmentTimer;
async function refreshDecision(){
  readForm();
  const before=JSON.stringify(state.draft);
  try{
    const result=await api('/api/assess',{case:state.draft});
    if(currentPage==='assess'&&before===JSON.stringify(state.draft))renderDecision($('decision-panel'),result.assessment);
  }catch(e){
    if($('decision-panel'))$('decision-panel').replaceChildren(el('div',{class:'danger-note'},e.message));
  }
}
function renderAssess(){
  state.draft=state.draft||blankCase();
  const root=$('assess');
  root.replaceChildren(heading(state.parentId?'Review an existing use case':'Assess a use case','Describe what happened, answer the questions, and the result updates as you go.'));
  const grid=el('div',{class:'assess-grid'}),left=el('form',{id:'assessment-form'}),right=el('div',{id:'decision-panel'});

  const extraction=panel(el('h2',{class:'panel-title'},'Describe the activity'),
    field('Name',input('case-name',state.name)),
    field('What did the employee do?',el('textarea',{id:'description',maxlength:1500,placeholder:'Which tool, what information, what task, and how the output was used or checked.'},state.description)));
  const where=boot.live_enabled?boot.provider+(boot.model?' ('+boot.model+')':''):'';
  if(boot.live_enabled){
    const consent=el('label',{class:'checkbox'},el('input',{id:'external-consent',type:'checkbox'}),'Send this description to '+where+'.');
    const classify=button('Suggest answers with AI',async()=>{
      readForm();
      if(!$('external-consent').checked){notice('Tick the box first to confirm the description may be sent to '+where+'.',true);return;}
      classify.disabled=true;classify.textContent='Working...';
      try{
        const result=await api('/api/classify',{description:state.description,confirm_external_processing:true});
        state.draft=result.case;state.classificationId=result.classification_id;
        renderAssess();
        notice('Suggestions filled in. Check every answer; a suggestion is not an approval.');
      }catch(e){notice(e.message,true);}
      finally{classify.disabled=false;classify.textContent='Suggest answers with AI';}
    });
    extraction.append(consent,classify);
  }else{
    extraction.append(el('p',{class:'hint'},'AI suggestions are off, so answer the questions yourself. Nothing you type leaves this computer.'));
  }

  const answers=panel(el('h2',{class:'panel-title'},'Check the answers'));
  const forms=el('div',{class:'forms-grid'});
  boot.forms.forEach(f=>forms.append(el('label',{class:'checkbox'},el('input',{type:'checkbox',id:'form-'+f.id,checked:state.draft.forms.includes(f.id)}),f.name)));
  answers.append(el('fieldset',{class:'choice-group',title:'Select all that apply. Leave empty if you are not sure.'},el('legend',{},'Kind of use'),forms));
  boot.dimensions.forEach(d=>answers.append(choiceGroup(d.id,d.name,[boot.unknown,...d.options],state.draft[d.id],d.question)));
  answers.append(choiceGroup('approval-status','Approved for this use?',boot.approval_options,state.draft.approval_status,'An enterprise licence does not mean every use is approved.'));

  const save=panel(el('h2',{class:'panel-title'},state.parentId?'Save a new revision':'Save your review'),
    el('div',{class:'two-up'},field('Owner of this use case',input('owner',state.owner,120)),field('Reviewed by',input('reviewer',state.reviewer,120))),
    field('Note (optional)',el('textarea',{id:'review-note',maxlength:1000,placeholder:'Anything the next reviewer should know.'},state.note)),
    el('label',{class:'checkbox'},el('input',{type:'checkbox',id:'confirm-review'}),'I have checked these answers. Saving does not approve this use.'),
    el('details',{class:'storage'},el('summary',{},'Storage options'),
      el('label',{class:'checkbox'},el('input',{type:'checkbox',id:'retain-description'}),'Also keep the description text in the local database. Off by default.'),
      el('p',{class:'hint'},'Names and notes are always stored. Keep sensitive details out of them.')),
    el('div',{class:'save-row'},el('button',{type:'submit',class:'primary',id:'save-record'},state.parentId?'Save revision':'Save review'),el('span',{id:'save-hint',class:'hint'})));

  left.append(extraction,answers,save);
  grid.append(left,right);root.append(grid);
  left.addEventListener('input',updateSaveState);
  left.addEventListener('change',()=>{
    updateSaveState();
    clearTimeout(assessmentTimer);
    assessmentTimer=setTimeout(refreshDecision,120);
  });
  left.addEventListener('submit',async event=>{
    event.preventDefault();readForm();
    const btn=$('save-record');btn.disabled=true;
    try{
      const record=await api('/api/records',{name:state.name,owner:state.owner,reviewer:state.reviewer,case:state.draft,classification_id:state.classificationId,description:state.description,retain_description:$('retain-description').checked,parent_id:state.parentId,review_note:state.note,confirm_review:$('confirm-review').checked});
      state.parentId=record.id;show('register');
      notice('Saved as revision '+record.revision+'. The result and the policy version are kept with it.');
    }catch(e){notice(e.message,true);updateSaveState();}
  });
  updateSaveState();
  refreshDecision();
}
function renderDecision(root,a){
  root.replaceChildren();
  const total=boot.dimensions.length+2;
  if(a.unresolved.length>=total){
    root.append(el('div',{class:'panel outcome-empty'},el('h2',{},'Your result will appear here'),el('p',{class:'quiet'},'Answer the questions on the left. Anything you are not sure about can stay as "Not sure yet", and the result will tell you what is still missing.')));
    return;
  }
  const outcome=panel(el('h2',{},a.outcome),el('p',{class:'quiet'},'What kind of review is needed under the sample policy. It is not a score or an approval.'));
  outcome.classList.add('outcome');
  const c=actionClass(a.outcome);
  if(c)outcome.classList.add(c);
  for(const hit of a.rule_hits)outcome.append(el('div',{class:'reason'},hit.reason));
  if(a.unresolved.length)outcome.append(el('div',{class:'unknown-box'},el('strong',{},'Still to answer: '),a.unresolved.map(id=>boot.dimensions.find(d=>d.id===id)?.name||(id==='forms'?'Kind of use':'Approved for this use?')).join(', ')));
  for(const n of a.notes)outcome.append(el('p',{class:'quiet'},n));
  outcome.append(el('div',{class:'hint',title:'The version of the sample policy used for this result.'},'Sample policy '+a.policy_version));
  root.append(outcome);
  if(a.risk_ids.length){
    root.append(el('h2',{class:'side-title'},a.risk_ids.length===1?'1 risk to manage':a.risk_ids.length+' risks to manage'));
    for(const id of a.risk_ids){
      const r=(a.risk_details||boot.risks).find(x=>x.id===id);
      root.append(el('details',{},el('summary',{},r.name),el('div',{class:'details-body'},
        el('p',{},el('strong',{},'Why it applies: '),a.risk_reasons[id]),
        el('p',{},el('strong',{},'Goal: '),r.control_objective),
        el('ul',{},r.illustrative_controls.map(s=>el('li',{},s))),
        el('p',{},el('strong',{},'Who is responsible: '),r.responsible_parties),
        el('p',{},el('strong',{},'What remains uncovered: '),r.remaining_limitation))));
    }
  }
  root.append(el('p',{class:'quiet baseline'},'Baseline controls always apply: '+a.baseline_controls.join(' ')));
}
async function renderRegister(){
  const root=$('register');
  root.replaceChildren(heading('Use-case register','Saved assessments, not example data. Each revision retains its own classification, review and policy snapshot.'));
  const records=await api('/api/records');
  const search=el('input',{
    id:'register-search',placeholder:'Filter by name, owner or outcome',type:'search','aria-label':'Filter saved assessments'
  }
  );
  root.append(el('div',{
    class:'toolbar'
  }
  ,search,el('div',{
    class:'actions'
  }
  ,el('a',{
    href:'/api/export/csv',class:'secondary'
  }
  ,'Export CSV'),el('a',{
    href:'/api/export/json',class:'secondary'
  }
  ,'Export full JSON'),button('New assessment',()=>newAssessment(),true))));
  const holder=el('div');
  root.append(holder,el('div',{
    id:'record-detail'
  }
  ));
  function renderRows(){
    const q=search.value.toLowerCase();
    const filtered=records.filter(r=>(r.name+' '+r.owner+' '+r.assessment.outcome).toLowerCase().includes(q));
    holder.replaceChildren();
    if(!filtered.length){
      holder.append(el('div',{
        class:'empty'
      }
      ,el('h2',{
      }
      ,records.length?'No matching records':'No assessments recorded yet'),el('p',{
      }
      ,'Explore a synthetic example, review its characteristics, and save an assessment to start your register.')));
      return;
    }
    const table=el('table',{
    }
    ,el('thead',{
    }
    ,el('tr',{
    }
    ,['Use case','Triage outcome','Owner','Revision','Saved'].map(h=>el('th',{
    }
    ,h)))));
    const tbody=el('tbody');
    filtered.forEach(r=>tbody.append(el('tr',{
    }
    ,el('td',{
    }
    ,el('button',{
      class:'link',on:{
        click:()=>recordDetail(r.id).catch(e=>notice(e.message,true))
      }
    }
    ,r.name)),el('td',{
    }
    ,badge(r.assessment.outcome)),el('td',{
    }
    ,r.owner),el('td',{
    }
    ,r.revision),el('td',{
    }
    ,r.created_at.slice(0,10)))));
    table.append(tbody);
    holder.append(el('div',{
      class:'table-wrap'
    }
    ,table),el('p',{
      class:'quiet'
    }
    ,filtered.length+' current assessment(s). Exports include all revisions.'));
  }
  search.addEventListener('input',renderRows);
  renderRows();
  const telemetry=await api('/api/events');
  if(telemetry.enabled){
    root.append(panel(el('h3',{
    }
    ,'Optional prompt-event metadata'),el('p',{
    }
    ,telemetry.events.length+' retained event(s). No prompt content is stored.'),el('p',{
      class:'quiet'
    }
    ,telemetry.note)));
  }
}
async function recordDetail(id){
  const data=await api('/api/records/'+encodeURIComponent(id));
  const r=data.record,root=$('record-detail');
  root.replaceChildren(el('h2',{
  }
  ,'Assessment history'),panel(el('h3',{
  }
  ,r.name),el('p',{
    class:'quiet'
  }
  ,'Recorded by '+r.reviewer+' / '+r.record_state),el('p',{
    class:'quiet'
  }
  ,'Policy '+r.assessment.policy_version+' / '+r.assessment.policy_sha256.slice(0,16)),button('Create a revised assessment',()=>{
    state.draft=structuredClone(r.case);
    state.name=r.name;
    state.owner=r.owner;
    state.reviewer='';
    state.note='';
    state.description=r.description||'';
    state.parentId=r.id;
    state.classificationId=null;
    show('assess');
  }
  ),...data.history.map(v=>el('div',{
    class:'revision-item'
  }
  ,'Revision '+v.revision+' / '+v.created_at+' / '+v.assessment.outcome))));
  const decision=el('div');
  root.append(decision);
  renderDecision(decision,r.assessment);
  if(Object.keys(r.corrections||{
  }
  ).length){
    root.append(panel(el('h3',{
    }
    ,'Recorded corrections'),...Object.entries(r.corrections).map(([key,value])=>el('p',{
    }
    ,key+': '+JSON.stringify(value.predicted)+' -> '+JSON.stringify(value.reviewed)))));
  }
  root.scrollIntoView({
    behavior:'smooth'
  }
  );
}
function renderFramework(){
  const root=$('framework');
  root.replaceChildren(heading('The research framework','Four forms, five dimensions and nine risk areas. Application triage rules are kept separate from the thesis taxonomy.'));
  const formPanel=panel(el('div',{
    class:'panel-label'
  }
  ,'TABLE 2 / FORMS OF EMPLOYEE USE'));
  boot.forms.forEach(f=>formPanel.append(el('div',{
    class:'definition'
  }
  ,el('strong',{
  }
  ,f.name),el('span',{
  }
  ,f.description))));
  const dimPanel=panel(el('div',{
    class:'panel-label'
  }
  ,'TABLE 3 / COMPARISON DIMENSIONS'));
  boot.dimensions.forEach(d=>dimPanel.append(el('div',{
    class:'definition'
  }
  ,el('strong',{
  }
  ,d.name),el('span',{
  }
  ,d.question))));
  root.append(formPanel,dimPanel,panel(el('h3',{
  }
  ,'What the software adds'),el('p',{
    class:'quiet'
  }
  ,'Explicit unknowns, multiple forms, use-approval context, LLM extraction, policy rules and revision records are software extensions. The thesis does not validate an automated classifier or assign formal risk ratings.')),el('h2',{
  }
  ,'Table 5 / Risk-to-control comparison'));
  boot.risks.forEach(r=>root.append(el('details',{
  }
  ,el('summary',{
  }
  ,r.name),el('div',{
    class:'details-body'
  }
  ,el('p',{
  }
  ,r.mechanism),el('p',{
  }
  ,el('strong',{
  }
  ,'Control objective: '),r.control_objective),el('ul',{
  }
  ,r.illustrative_controls.map(c=>el('li',{
  }
  ,c))),el('p',{
  }
  ,el('strong',{
  }
  ,'Responsibilities: '),r.responsible_parties),el('p',{
  }
  ,el('strong',{
  }
  ,'Limitation: '),r.remaining_limitation)))));
  root.append(el('p',{
    class:'quiet'
  }
  ,'Source: Delegeanu, D. (2026). The Use of Generative Artificial Intelligence in Banks: Governance, Risks, and Internal Controls. Bocconi University. Sections 3.2, 3.3 and 5.2-5.6.'));
}
function renderValidation(){
  const root=$('validation');
  root.replaceChildren(heading('Test results','Software tests, extraction evaluation and real-world effectiveness answer different questions. Keep their results separate.'),el('div',{
    class:'danger-note'
  }
  ,el('strong',{
  }
  ,'Live-model accuracy is not established. '),'No model benchmark or banking effectiveness result is implied by a passing software test suite.'));
  root.append(el('div',{
    class:'validation-grid'
  }
  ,panel(el('div',{
    class:'panel-label'
  }
  ,'01 / SOFTWARE BEHAVIOUR'),el('h2',{
  }
  ,'Run the offline checks'),el('p',{
    class:'quiet'
  }
  ,'Test policy decisions, parsing, storage, revisions, export safety, API boundaries and the metadata hook without calling a model.'),el('pre',{
  }
  ,'python -m pytest -q\npython -m eval.run_eval --validate-only')),panel(el('div',{
    class:'panel-label'
  }
  ,'02 / MODEL EXTRACTION'),el('h2',{
  }
  ,'Measure, then publish'),el('p',{
    class:'quiet'
  }
  ,'The benchmark reports attempted cases, failures, per-field accuracy, risk-set agreement and missed escalations. Synthetic labels are not expert consensus.'),el('pre',{
  }
  ,'python -m eval.run_eval --live \\\n  --output eval/results/run.json')),panel(el('div',{
    class:'panel-label'
  }
  ,'03 / REAL-WORLD VALIDITY'),el('h2',{
  }
  ,'Not demonstrated'),el('p',{
    class:'quiet'
  }
  ,'The project has not been evaluated against original bank workflows, validated by an independent banking panel or shown to reduce operational losses.')),panel(el('div',{
    class:'panel-label'
  }
  ,'04 / KNOWN BOUNDARIES'),el('h2',{
  }
  ,'Local, single-user prototype'),el('p',{
    class:'quiet'
  }
  ,'No authenticated reviewer identity, encryption at rest, enterprise enforcement or tamper-proof audit store. A risk flag is not proof that a control operated.'))));
}
document.querySelectorAll('nav button').forEach(b=>b.addEventListener('click',()=>show(b.dataset.page)));
api('/api/bootstrap').then(data=>{
  boot=data;
  $('version').textContent='v'+boot.version;
  $('mode-label').textContent=boot.live_enabled?'AI suggestions on':'AI suggestions off';
  $('mode-label').title=boot.live_enabled?'Descriptions are sent to '+boot.provider+' only when you ask for a suggestion and confirm.':'Nothing you type leaves this computer. Turn AI suggestions on in .env (see the README).';
  show('overview');
}
).catch(e=>notice('Could not start the workspace: '+e.message,true));
