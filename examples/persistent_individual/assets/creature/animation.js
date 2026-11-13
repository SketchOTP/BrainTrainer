/* Original supplied pixels; display-only projection, never a brain input. */
const CreatureAnimation = (() => {
  const clips = {
    idle: {sheet:1,row:0,frames:[0,1,2,3,4,5,6,7],fps:6,label:'Attentive'},
    left: {sheet:1,row:4,frames:[0,1,2,3,6,7],fps:8,label:'Moving left'},
    right: {sheet:1,row:5,frames:[0,1,2,3,6,7],fps:8,label:'Moving right'},
    rest: {sheet:4,row:1,frames:[4,5,6,5],fps:3,label:'Resting'},
    eat: {sheet:3,row:2,frames:[0,1,2,3,4,5,6,7],fps:7,label:'Eating'},
    practice: {sheet:1,row:7,frames:[0,1,2,3,4,6,7],fps:7,label:'Interacting'},
    rehearse: {sheet:3,row:4,frames:[0,1,2,3,4,5,6,7],fps:6,label:'Rehearsing recorded experience'},
    learned: {sheet:3,row:7,frames:[0,1,2,3,4,5,6,7],fps:7,label:'Retained a code improvement'},
    request: {sheet:1,row:3,frames:[0,1,2,3,6,7],fps:4,label:'Requesting assistance'},
  };
  function select(state) {
    const event=state.event, outcome=event?.outcome, motion=event?.body_motion;
    if(outcome?.status==='rested')return 'rest';
    if(motion && motion.after!==motion.before)return motion.after<motion.before?'left':'right';
    if(outcome?.completed && outcome?.energy_delta>0)return 'eat';
    if(outcome?.status==='activated')return 'practice';
    if(state.requests?.length)return 'request';
    return 'idle';
  }
  function mount(canvas) {
    const context=canvas.getContext('2d');context.imageSmoothingEnabled=false;
    const images={};let state=null,clip='idle',started=performance.now(),until=0,lastKey=null,previous=null,lastFrame='',connected=true;
    for(let n=1;n<=4;n++){const image=new Image();images[n]=image;image.onload=()=>{lastFrame='';};image.src=`/assets/creature/sheet-${n}.png`;}
    function disconnect() {
      connected=false;until=0;previous=null;lastKey=null;
      canvas.setAttribute('aria-label','Creature · connection lost; current activity unknown');
    }
    function update(next) {
      if(!connected)lastFrame='';
      connected=true;
      const key=`${next.tick}:${next.event_count}`;const now=performance.now();
      if(key!==lastKey){
        let selected=select(next);
        if(previous && next.revision_count>previous.revision_count)selected='learned';
        else if(previous && next.dream_count>previous.dream_count)selected='rehearse';
        if(selected!==clip || !next.running){clip=selected;started=now;}
        // One-step actions have a finite display interval; loading a paused save does not replay it.
        until=previous?now+(selected==='learned'||selected==='rehearse'?1400:700):0;
        lastKey=key;
      }
      if(previous?.running && !next.running)until=0;
      previous=next;state=next;
      canvas.setAttribute('aria-label',`Creature · ${next.running?clips[clip].label:'paused'}`);
    }
    function draw(now) {
      const playing=connected && state && (state.running || now<until);
      const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
      const definition=clips[clip];
      // Freeze when paused. Reduced motion uses a representative frame, preserving the state cue.
      if(playing && !reduced || !lastFrame){
        const frame=reduced?0:Math.floor((now-started)*definition.fps/1000)%definition.frames.length;
        const col=definition.frames[frame],image=images[definition.sheet];
        const key=`${clip}:${col}`;
        if(image.complete && image.naturalWidth && key!==lastFrame){
          const x=Math.round(col*image.naturalWidth/8),y=Math.round(definition.row*image.naturalHeight/8);
          const w=Math.round((col+1)*image.naturalWidth/8)-x,h=Math.round((definition.row+1)*image.naturalHeight/8)-y;
          context.clearRect(0,0,157,157);context.drawImage(image,x,y,w,h,0,157-h,w,h);
          canvas.dataset.clip=clip;canvas.dataset.frame=String(col);lastFrame=key;
        }
      }
      requestAnimationFrame(draw);
    }
    requestAnimationFrame(draw);return {update,disconnect};
  }
  return {clips,select,mount};
})();
if(typeof module!=='undefined')module.exports=CreatureAnimation;
