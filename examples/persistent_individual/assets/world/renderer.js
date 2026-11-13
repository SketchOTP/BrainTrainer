/* Render only recorded world positions. Camera controls never move the creature. */
const CreatureWorld=(()=>{
 function mount(container){
  const canvas=document.createElement('canvas');canvas.id='world-canvas';canvas.setAttribute('role','img');canvas.setAttribute('aria-label','Creature overworld');container.append(canvas);
  const ctx=canvas.getContext('2d'),mapImage=new Image(),sheets={};mapImage.src='/assets/world/atlas.png';const environmentImages={};
  for(const name of ['movement','daily','expressions']){sheets[name]=new Image();sheets[name].src=`/assets/creature/etch-v3/${name}.png`;}
  const clips={idle:{sheet:'daily',row:0,fps:3},rest:{sheet:'daily',row:1,fps:2},eat:{sheet:'daily',row:2,fps:6},practice:{sheet:'daily',row:3,fps:6},rehearse:{sheet:'expressions',row:0,fps:4},request:{sheet:'expressions',row:1,fps:4},learned:{sheet:'expressions',row:2,fps:5}};
  // Bake each source frame once onto the same world-pixel grid as the map.
  // Camera zoom enlarges those pixels; movement cannot resample the source art.
  const frameCache=new Map(),terrainCache=new Map();
  // A small overworld palette and solid pixel edges match the map's sprites.
  // This is a cached display texture; the supplied source PNGs remain intact.
  const creaturePalette=['#343443','#4b455b','#625570','#7b6b8b','#9585a5','#b1a2bd','#d1c3d6','#e6dbdf','#5b5147','#807052','#aa9060','#c9b17a','#e6ce99','#f4e4bc','#93652d','#cf8a30','#f2ad35','#ffda71'].map(hex=>[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)));
  function sprite(sheet,row,col,x,y){
   const img=sheets[sheet];if(!img.complete||!img.naturalWidth)return;
   const key=`${sheet}:${row}:${col}`;let tile=frameCache.get(key);
   if(!tile){
    tile=document.createElement('canvas');tile.width=28;tile.height=28;
    const pixels=tile.getContext('2d');pixels.imageSmoothingEnabled=true;pixels.imageSmoothingQuality='high';
    const left=Math.round(col*img.naturalWidth/4),top=Math.round(row*img.naturalHeight/4),right=Math.round((col+1)*img.naturalWidth/4),bottom=Math.round((row+1)*img.naturalHeight/4);
    pixels.drawImage(img,left,top,right-left,bottom-top,0,0,28,28);
    const texture=pixels.getImageData(0,0,28,28),rgba=texture.data;
    for(let i=0;i<rgba.length;i+=4){
     if(rgba[i+3]<112){rgba[i+3]=0;continue}
     let best=creaturePalette[0],distance=Infinity;
     for(const color of creaturePalette){const d=(rgba[i]-color[0])**2+2*(rgba[i+1]-color[1])**2+(rgba[i+2]-color[2])**2;if(d<distance){best=color;distance=d}}
     rgba[i]=best[0];rgba[i+1]=best[1];rgba[i+2]=best[2];rgba[i+3]=255;
    }
    pixels.putImageData(texture,0,0);frameCache.set(key,tile);
   }
   const baseline=sheet==='daily'&&row===1?23:25;
   ctx.drawImage(tile,Math.round(x)-14,Math.round(y)-baseline);
  }
  const propPixels={
   lantern:[
    '....ooo.....','...obbo.....','...o..o.....','..oooooo....',
    '.obbbbbbo...','..obbbbo....','..oggggo....','..oghggo....',
    '..oggggo....','..oggggo....','..oggggo....','..obbbbo....',
    '.obbbbbo....','..oooooo....','...oooo.....','............'
   ],
   stone:[
    '............','............','............','............',
    '....oooo....','..oossssoo..','.osshsssssso','.osssmssmsso',
    'osssssssssso','osssssssssso','.osssssssso.',
    '..oooooooo..','............','............','............','............'
   ],
   food:[
    '............','............','............','.....ll.....',
    '....ol......','...offffo...','..ofhffffo..','..offffffo..',
    '...offffo...','..obbbbbbo..','...obbbbo...','....oooo....',
    '............','............','............','............'
   ]
  };
  function drawProp(o,x,y){
   const stone=['counter','inert'].includes(o.function),kind=o.food?'food':stone?'stone':'lantern';
   const palette={o:'#4d5149',b:'#ac874c',g:o.state?'#e6c76c':'#819c92',h:o.food?'#f4d49b':o.state?'#fff0b0':'#b7c6ad',s:'#929c89',m:o.state?'#dbc97f':'#65786c',l:'#638447',f:o.identity==='object-0'?'#c97658':'#8b789d'};
   const left=Math.round(x)-6,top=Math.round(y)-13;
   ctx.fillStyle='#344b3438';ctx.fillRect(left+2,Math.round(y),8,2);
   propPixels[kind].forEach((line,row)=>[...line].forEach((pixel,col)=>{if(pixel!=='.'){ctx.fillStyle=palette[pixel];ctx.fillRect(left+col,top+row,1,1)}}));
  }
  let expression='idle',expressionStart=0,expressionUntil=0,expressionFrame=0,lastEventKey=null;
  let data=null,state=null,connected=true,pose=null,queue=[],segment=null,lastTick=-1,frame=0,lastTime=0,follow=true,overview=false,zoom=3,camera={x:160,y:160},drag=null;
  let loadedMapUrl=null;
  function loadMap(url){loadedMapUrl=url;fetch(url).then(r=>{if(!r.ok)throw Error('World map could not load');return r.json()}).then(v=>{if(loadedMapUrl===url){data=v;terrainCache.clear();mapImage.src=v.atlas_url||'/assets/world/atlas.png';}}).catch(()=>{if(loadedMapUrl===url){canvas.setAttribute('aria-label','World map unavailable');region.textContent='Map unavailable · reload to retry'}});}

  const hud=document.createElement('div');hud.className='world-hud';const region=document.createElement('span');region.className='world-region';const controls=document.createElement('div');
  for(const [label,action] of [['−',()=>{overview=false;zoom=Math.max(.5,zoom>=2?Math.floor(zoom)-1:zoom-.25)}],['+',()=>{overview=false;zoom=Math.min(5,Math.floor(zoom)+1)}],['Follow',()=>{overview=false;follow=true}],['Overview',()=>{overview=true;follow=false}]]){const b=document.createElement('button');b.textContent=label;b.type='button';b.onclick=action;controls.append(b)}hud.append(region,controls);container.append(hud);
  canvas.onpointerdown=e=>{overview=false;drag={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);follow=false};canvas.onpointermove=e=>{if(!drag)return;camera.x-=(e.clientX-drag.x)/zoom;camera.y-=(e.clientY-drag.y)/zoom;drag={x:e.clientX,y:e.clientY}};canvas.onpointerup=()=>drag=null;canvas.onpointercancel=()=>drag=null;
  canvas.onwheel=e=>{e.preventDefault();overview=false;zoom=Math.max(1,Math.min(5,zoom-Math.sign(e.deltaY))) };
  function update(s){
   const prior=state;connected=true;state=s;for(const object of s.environment_objects||[]){const asset=object.visual.asset;if(!environmentImages[asset]){environmentImages[asset]=new Image();environmentImages[asset].src=asset}}if(!s.world){container.classList.remove('topdown');return}container.classList.add('topdown');
   const mapUrl=s.world.map_url||'/assets/world/maps.json';if(mapUrl!==loadedMapUrl)loadMap(mapUrl);
   const key=`${s.tick}:${s.event_count}`;
   if(key!==lastEventKey){
    let selected=CreatureAnimation.select(s);if(['left','right'].includes(selected))selected='idle';
    if(prior&&s.revision_count>prior.revision_count)selected='learned';
    else if(prior&&s.dream_count>prior.dream_count)selected='rehearse';
    if(selected!==expression){expression=selected;expressionStart=performance.now();expressionFrame=0}
    expressionUntil=prior?performance.now()+(['learned','rehearse'].includes(selected)?1400:700):0;lastEventKey=key;
   }
   if(prior?.running&&!s.running)expressionUntil=0;
   region.textContent=data?.labels?.[s.world.region]||s.world.region.replace('MAP_','').replaceAll('_',' ').toLowerCase();
   if(pose===null){pose={...s.world};lastTick=s.tick;queue=[];segment=null}
   else if(s.tick>lastTick){
    const steps=(s.world_trace||[]).filter(p=>p.tick>lastTick);
    if(steps.length && steps[0].tick===lastTick+1 && steps.length<=8)queue.push(...steps.map(p=>p.after));
    else {pose={...s.world};queue=[];segment=null}
    lastTick=s.tick;
   }
   if(!s.running){pose={...s.world};queue=[];segment=null}
  }
  function disconnect(){connected=false;queue=[];segment=null;canvas.setAttribute('aria-label','World connection lost; current activity unknown')}
  function draw(now){
   const delta=Math.min(100,now-(lastTime||now));lastTime=now;frame+=delta;
   if(state?.world&&data&&pose){
    if(connected&&state.running){
     if(!segment&&queue.length)segment={from:{...pose},to:queue.shift(),elapsed:0,duration:queue.length>2?200:420};
     if(segment){segment.elapsed+=delta;let t=Math.min(1,segment.elapsed/segment.duration);if(segment.to.region===segment.from.region){pose={...segment.to,x:segment.from.x+(segment.to.x-segment.from.x)*t,y:segment.from.y+(segment.to.y-segment.from.y)*t}}else pose={...segment.to};if(t===1)segment=null}
    }
    const width=container.clientWidth,height=container.clientHeight;if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height}ctx.imageSmoothingEnabled=false;
    const m=data.maps[pose.region];if(!m){requestAnimationFrame(draw);return}
    if(overview){
     const fit=Math.min((width-24)/(m.width*16),(height-80)/(m.height*16));
     zoom=fit<1?fit:Math.floor(fit);camera={x:m.width*8,y:m.height*8};
    }
    if(follow){
     const clamp=(v,size,view)=>size<=view?size/2:Math.max(view/2,Math.min(size-view/2,v));
     camera.x=clamp(pose.x*16+8,m.width*16,width/zoom);camera.y=clamp(pose.y*16+8,m.height*16,height/zoom);
    }
    ctx.fillStyle='#192e2e';ctx.fillRect(0,0,width,height);ctx.save();ctx.translate(Math.round(width/2-camera.x*zoom),Math.round(height/2-camera.y*zoom));ctx.scale(zoom,zoom);
    if(mapImage.complete&&mapImage.naturalWidth){
     let terrain=terrainCache.get(pose.region);
     if(!terrain){
      terrain=document.createElement('canvas');terrain.width=m.width*16;terrain.height=m.height*16;
      const terrainContext=terrain.getContext('2d');terrainContext.imageSmoothingEnabled=false;
      for(let y=0;y<m.height;y++)for(let x=0;x<m.width;x++){const tile=m.tiles[y*m.width+x];terrainContext.drawImage(mapImage,(tile%data.atlas_columns)*16,Math.floor(tile/data.atlas_columns)*16,16,16,x*16,y*16,16,16)}
      terrainCache.set(pose.region,terrain);
     }
     // Scale one continuous surface so fractional phone overview cannot expose tile seams.
     ctx.drawImage(terrain,0,0);
    }
    const things=(state.objects||[]).filter(o=>o.visible&&o.region===pose.region&&o.function!=='berry-plot').map(o=>({y:o.y,object:o}));for(const object of state.environment_objects||[])if(object.position.region===pose.region)things.push({y:object.position.y,environment:object});things.push({y:pose.y,actor:true});things.sort((a,b)=>a.y-b.y);
    const moving=connected&&state.running&&segment&&segment.from.region===segment.to.region&&(segment.from.x!==segment.to.x||segment.from.y!==segment.to.y);
    const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
    for(const thing of things){
     if(thing.actor){
      const x=Math.round(pose.x*16+8),y=Math.round(pose.y*16+12);ctx.fillStyle='#344b3438';ctx.fillRect(x-4,y-1,8,2);ctx.fillRect(x-3,y+1,6,1);
      const row={south:0,west:1,east:2,north:3}[pose.facing]??0;
      const expressive=!moving&&expression!=='idle'&&(!['learned','rehearse'].includes(expression)||now<expressionUntil);
      if(expressive){
       const clip=clips[expression];
       if(connected&&(state.running||now<expressionUntil)&&!reduced)expressionFrame=Math.floor((now-expressionStart)*clip.fps/1000)%4;
       const index=reduced?0:expressionFrame;sprite(clip.sheet,clip.row,index,x,y);
       canvas.dataset.clip=expression;canvas.dataset.frame=String(index);
      }else if(moving){
       const col=reduced?0:Math.floor(frame/140)%4;sprite('movement',row,col,x,y);canvas.dataset.clip='walk';canvas.dataset.frame=String(col);
      }else{
       const col=connected&&state.running&&!reduced?Math.floor(frame/350)%4:0;
       if(pose.facing==='south')sprite('daily',0,col,x,y);else sprite('movement',row,0,x,y);
       canvas.dataset.clip='idle';canvas.dataset.frame=String(pose.facing==='south'?col:0);
      }
      canvas.dataset.facing=pose.facing;canvas.dataset.walking=String(Boolean(moving));canvas.dataset.region=pose.region;canvas.dataset.x=pose.x.toFixed(3);canvas.dataset.y=pose.y.toFixed(3);
     }else if(thing.environment){
      const {position:p,visual:v}=thing.environment,img=environmentImages[v.asset];
      if(img?.complete&&img.naturalWidth)ctx.drawImage(img,v.frame*v.frame_width,0,v.frame_width,v.frame_height,p.x*16,p.y*16-v.anchor_y,v.frame_width,v.frame_height);
     }else{
      const o=thing.object;drawProp(o,o.x*16+8,o.y*16+12);
     }
    }
    ctx.restore();if(connected)canvas.setAttribute('aria-label',`Creature in ${region.textContent}, facing ${pose.facing}${moving?', walking':''}`);
   }
   requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);return{update,disconnect};
 }
 return{mount};
})();
