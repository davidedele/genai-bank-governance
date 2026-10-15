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

function copyText(text,btn){
  const done=()=>{const old=btn.textContent;btn.textContent='Copied';setTimeout(()=>{btn.textContent=old;},1500);};
  try{navigator.clipboard.writeText(text).then(done,()=>{});}catch(e){}
}
function openDialog(title,...children){
  const d=el('dialog',{class:'modal','aria-label':title});
  const close=el('button',{type:'button',class:'modal-close','aria-label':'Close'},'×');
  close.addEventListener('click',()=>d.close());
  d.addEventListener('click',e=>{if(e.target===d)d.close();});
  d.addEventListener('close',()=>d.remove());
  d.append(close,el('h2',{},title),...children);
  document.body.append(d);
  d.showModal();
  return d;
}
function aiPaused(){
  try{return localStorage.getItem('ai-paused')==='1';}catch(e){return false;}
}
function setAiPaused(v){
  try{localStorage.setItem('ai-paused',v?'1':'0');}catch(e){}
}
function aiUsable(){return boot.live_enabled&&!aiPaused();}
function updatePill(){
  const pill=$('mode-label');
  pill.textContent=!boot.live_enabled?'AI suggestions off':aiPaused()?'AI suggestions paused':'AI suggestions on';
  pill.classList.toggle('on',aiUsable());
}
const ENV_SNIPPET='ENABLE_LIVE_CLASSIFICATION=1\nLLM_PROVIDER=openai\nLLM_MODEL=the-model-name-from-your-provider-account\nOPENAI_API_KEY=your-key';
function openAiDialog(){
  const body=[];
  body.push(el('p',{},'On the Assess page, an AI model can read your description of what an employee did and suggest the answers to the questions. You always check the answers yourself, and the fixed rules (not the AI) decide the result.'));
  if(!boot.live_enabled){
    const pre=el('pre',{},ENV_SNIPPET);
    const copy=el('button',{type:'button',class:'secondary button-small'},'Copy these lines');
    copy.addEventListener('click',()=>copyText(ENV_SNIPPET,copy));
    body.push(el('div',{class:'modal-state off'},'Right now: off'),
      el('p',{},'It is off because it needs an account with an AI provider (OpenAI, Anthropic, Google or xAI) and a private key, which can cost a little money. While it is off, nothing you type leaves this computer, and you answer the questions yourself. Everything else in the app works normally.'),
      el('h3',{},'To turn it on'),
      el('ol',{class:'how'},
        el('li',{},'Stop the app in the terminal with Ctrl+C.'),
        el('li',{},'Run ',el('code',{},'python -m pip install -r requirements-llm.txt')),
        el('li',{},'Copy ',el('code',{},'.env.example'),' to ',el('code',{},'.env'),' and fill in these lines with your own provider, model and key:',pre,copy),
        el('li',{},'Start the app again with ',el('code',{},'python app.py'),'.')));
    body.push(el('p',{class:'hint'},'There is no switch on this page because the key must stay in your own file. This app never asks you to type it here.'));
  }else{
    const label=el('label',{class:'checkbox'});
    const box=el('input',{type:'checkbox',checked:!aiPaused()});
    box.addEventListener('change',()=>{setAiPaused(!box.checked);updatePill();if(currentPage==='assess')renderAssess();});
    label.append(box,'Use AI suggestions in this browser');
    body.push(el('div',{class:'modal-state on'},'Right now: '+(aiPaused()?'paused':'on')),
      el('p',{},'Provider: '+boot.provider+(boot.model?', model: '+boot.model:'')+'. A description is sent only when you tick the confirmation box and press "Suggest answers with AI". You can make up to '+(boot.daily_limit||'any number of')+' suggestions a day.'),
      label,
      el('p',{class:'hint'},'Untick to pause them here without changing any settings. To turn them off completely, set ENABLE_LIVE_CLASSIFICATION=0 in your .env file and restart the app.'));
  }
  openDialog('AI suggestions',...body);
}

function flow(steps,active=-1,done=[]){
  const ol=el('ol',{class:'flow'});
  steps.forEach((s,i)=>ol.append(el('li',{class:(done.includes(i)?'done ':'')+(i===active?'current':'')},
    el('span',{class:'flow-dot'},done.includes(i)?'✓':String(i+1)),
    el('strong',{},s[0]),el('span',{class:'flow-text'},s[1]))));
  return ol;
}
const ASSESS_STEPS=[['Describe','Say what the employee did.'],['Answer','Pick the closest answer to each question.'],['Save','Add who owns and who reviewed it.']];
function updateFlow(){
  const holder=$('assess-flow');
  if(!holder)return;
  const described=!!(state.name.trim()||state.description.trim());
  const answered=state.draft.forms.length>0||boot.dimensions.some(d=>state.draft[d.id]!==boot.unknown)||state.draft.approval_status!==boot.unknown;
  const ready=!$('save-record').disabled;
  const done=[];
  if(described)done.push(0);
  if(answered)done.push(1);
  if(ready)done.push(2);
  const active=[0,1,2].find(i=>!done.includes(i));
  holder.replaceChildren(flow(ASSESS_STEPS,active===undefined?-1:active,done));
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
  root.append(el('div',{class:'how-it-works'},el('h2',{},'How it works'),flow([['Describe','What did the employee do with an AI tool?'],['Answer','Pick the closest answer to a few questions.'],['See the result','Which risks, controls and review apply.'],['Save','Keep a dated record you can revise later.']])));
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
function input(id,value='',max=160,placeholder=''){
  return el('input',{
    id,value,maxlength:max,placeholder
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
  if(!state.name.trim())missing.push('a title');
  if(!state.owner.trim())missing.push('an owner');
  if(!state.reviewer.trim())missing.push('a reviewer');
  if(!$('confirm-review').checked)missing.push('your confirmation');
  save.disabled=missing.length>0;
  $('save-hint').textContent=missing.length?'To save, add '+missing.join(', ')+'.':'';
  updateFlow();
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
  root.replaceChildren(heading(state.parentId?'Review an existing use case':'Assess a use case','Describe what happened, answer the questions, and the result updates as you go.'),el('div',{id:'assess-flow',class:'assess-flow'}));
  const grid=el('div',{class:'assess-grid'}),left=el('form',{id:'assessment-form'}),right=el('div',{id:'decision-panel'});

  const extraction=panel(el('h2',{class:'panel-title'},'Describe the activity'),
    field('Short title for this use case',input('case-name',state.name,160,'For example: Summarizing a client email'),'This is how it will be listed in the register.'),
    field('What did the employee do?',el('textarea',{id:'description',maxlength:1500,placeholder:'Which tool, what information, what task, and how the output was used or checked.'},state.description)));
  const where=boot.live_enabled?boot.provider+(boot.model?' ('+boot.model+')':''):'';
  if(aiUsable()){
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
    const why=el('button',{type:'button',class:'link'},boot.live_enabled?'AI suggestions are paused. What is this?':'AI suggestions are off. What is this?');
    why.addEventListener('click',openAiDialog);
    extraction.append(el('p',{class:'hint'},'Nothing you type leaves this computer. ',why));
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
      ,records.length?'No matching records':'Nothing saved yet'),el('p',{
      }
      ,records.length?'Try a different search.':'This is where your saved reviews will appear. It is empty because you have not saved one yet.')));
      if(!records.length){
        holder.append(el('div',{class:'panel register-empty'},el('h3',{},'Want to see how it works? Try this:'),
          flow([['Open an example','It fills in the questions for you.'],['Look at the result','It shows the risks and controls on the right.'],['Save it','Add an owner and a reviewer, tick the box and press Save review. It then appears here.']]),
          el('div',{class:'actions'},button('Try an example',()=>newAssessment(boot.examples[0]),true),button('Start from scratch',()=>newAssessment())),
          el('p',{class:'hint'},'Everything you save stays in a file on this computer.')));
      }
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
function evidenceCard(status,tone,question,...children){
  return el('div',{class:'panel evidence'},el('span',{class:'chip '+tone},status),el('h2',{},question),...children);
}
function renderValidation(){
  const root=$('validation');
  const b=boot.benchmark;
  root.replaceChildren(heading('Test results','Three different questions about whether this works. Each has its own answer, and they should not be mixed up.'));
  root.append(el('div',{class:'evidence-grid'},
    evidenceCard('Checked automatically','ok','Does the software behave correctly?',
      el('p',{},'Yes, as far as the automated tests go. They check that the rules give the same result every time, that saving and revising keep old records safe, that exports are safe to open in a spreadsheet, and that the pages load. One test tries every valid combination of answers (1,440 of them).'),
      el('p',{class:'quiet'},'To run them yourself:'),el('pre',{},'python -m pip install -r requirements-dev.txt\npython -m pytest -q')),
    evidenceCard('Not measured yet','todo','Does the AI suggest the right answers?',
      el('p',{},'Live-model accuracy is not established. There is a practice set of '+b.prompts+' made-up descriptions covering '+b.scenarios+' situations, each with the answers I expect. Running it shows how often a model agrees with me. I have not published a result, and I wrote the expected answers myself, so no bank professional has checked them.'),
      el('p',{class:'quiet'},'To run it you need AI suggestions switched on, and it costs a little money:'),el('pre',{},'python -m eval.run_eval --live --output eval/results/run.json')),
    evidenceCard('Not tested','todo','Would it help in a real bank?',
      el('p',{},'Unknown. It has not been tried on real bank processes, reviewed by an independent panel, or shown to reduce problems. The risks, controls and rules come from my thesis, which is a literature study, so treat them as a starting point for discussion.'))));
  root.append(el('div',{class:'panel'},el('h2',{},'What this means for you'),
    el('p',{},'You can rely on the rules to behave consistently, and you can see exactly why each outcome appeared. You should not treat any outcome as advice, a risk rating or an approval.'),
    el('p',{class:'quiet'},'Limits of this prototype: it has no login, saved files are not encrypted, and the history is not tamper-proof. Use it on your own computer with made-up information.')));
}
document.querySelectorAll('nav button').forEach(b=>b.addEventListener('click',()=>show(b.dataset.page)));
api('/api/bootstrap').then(data=>{
  boot=data;
  $('version').textContent='v'+boot.version;
  updatePill();
  $('mode-label').addEventListener('click',openAiDialog);
  show('overview');
}
).catch(e=>notice('Could not start the workspace: '+e.message,true));
