/* Render only recorded world positions. Camera controls never move the creature. */
const CreatureWorld=(()=>{
 function mount(container){
  const canvas=document.createElement('canvas');canvas.id='world-canvas';canvas.setAttribute('role','img');canvas.setAttribute('aria-label','Creature overworld');container.append(canvas);
  const ctx=canvas.getContext('2d'),mapImage=new Image(),sheets={},updatedCharacter=new Image();mapImage.src='/assets/world/atlas.png';const environmentImages={};
  for(const name of ['movement','daily','expressions']){sheets[name]=new Image();sheets[name].src=`/assets/creature/etch-v3/${name}.png`;}
  updatedCharacter.src='/assets/interactive-art/v1/manipulation.png';
  const clips={idle:{sheet:'daily',row:0,fps:3},rest:{sheet:'daily',row:1,fps:2},eat:{sheet:'daily',row:2,fps:6},practice:{sheet:'daily',row:3,fps:6},rehearse:{sheet:'expressions',row:0,fps:4},request:{sheet:'expressions',row:1,fps:4},learned:{sheet:'expressions',row:2,fps:5}};
  // Keep the full-colour source detail in the cached world sprite. The older
  // 28px palette pass made the creature visibly coarser than current town art.
  const frameCache=new Map(),terrainCache=new Map();
  const creatureFrameSize=84,creatureTextureSize=64,creatureScale=creatureFrameSize/56;
  function sprite(sheet,row,col,x,y){
   const img=sheets[sheet];if(!img.complete||!img.naturalWidth)return;
   const key=`${sheet}:${row}:${col}`;let tile=frameCache.get(key);
   if(!tile){
    tile=document.createElement('canvas');tile.width=creatureTextureSize;tile.height=creatureTextureSize;
    const pixels=tile.getContext('2d');pixels.imageSmoothingEnabled=true;pixels.imageSmoothingQuality='high';
    const left=Math.round(col*img.naturalWidth/4),top=Math.round(row*img.naturalHeight/4),right=Math.round((col+1)*img.naturalWidth/4),bottom=Math.round((row+1)*img.naturalHeight/4);
    pixels.drawImage(img,left,top,right-left,bottom-top,0,0,creatureTextureSize,creatureTextureSize);
    const enlarged=document.createElement('canvas');enlarged.width=creatureFrameSize;enlarged.height=creatureFrameSize;
    const crisp=enlarged.getContext('2d');crisp.imageSmoothingEnabled=false;
    crisp.drawImage(tile,0,0,creatureTextureSize,creatureTextureSize,0,0,creatureFrameSize,creatureFrameSize);tile=enlarged;frameCache.set(key,tile);
   }
   const baseline=(sheet==='daily'&&row===1?46:50)*creatureScale;
   ctx.drawImage(tile,Math.round(x)-creatureFrameSize/2,Math.round(y)-baseline);
  }
  function currentCharacter(facing,col,x,y){
   if(!updatedCharacter.complete||!updatedCharacter.naturalWidth)return false;
   // The updated 128px sheet keeps the existing purple companion design and
   // supplies front, left, right and back views in its four rows.
   const row={south:0,west:1,east:2,north:3}[facing]??0;
   ctx.save();ctx.imageSmoothingEnabled=false;
   ctx.drawImage(updatedCharacter,(col%4)*128,row*128,128,128,
    Math.round(x)-creatureFrameSize/2,Math.round(y)-50*creatureScale,
    creatureFrameSize,creatureFrameSize);
   ctx.restore();return true;
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
  let data=null,state=null,connected=true,pose=null,queue=[],segment=null,lastTick=-1,frame=0,lastTime=0,follow=false,overview=true,zoom=3,camera={x:160,y:160},drag=null;
  let loadedMapUrl=null;
  function loadVisual(visual){const asset=visual?.atlas_url||visual?.asset;if(asset&&!environmentImages[asset]){environmentImages[asset]=new Image();environmentImages[asset].src=asset}if(visual?.underlay)loadVisual(visual.underlay)}
  function loadMap(url){loadedMapUrl=url;fetch(url).then(r=>{if(!r.ok)throw Error('World map could not load');return r.json()}).then(v=>{if(loadedMapUrl===url){data=v;terrainCache.clear();mapImage.src=v.atlas_url||'/assets/world/atlas.png';loadVisual({atlas_url:'/assets/interactive-art/v1/buildings.png'});for(const placement of v.scene_layout?.placements||[])loadVisual(placement.visual)}}).catch(()=>{if(loadedMapUrl===url){canvas.setAttribute('aria-label','World map unavailable');region.textContent='Map unavailable · reload to retry'}});}
  function drawVisual(visual,position,tileSize){
   const img=environmentImages[visual.atlas_url||visual.asset];if(!img?.complete||!img.naturalWidth)return;
   if(Number.isInteger(visual.row)&&Number.isInteger(visual.frame_size)){
    const facing=visual.facing||['south','east','north','west'][((Math.round((visual.rotation_degrees||0)/90)%4)+4)%4];
    const column=visual.fixed_view?(Number.isInteger(visual.frame)?visual.frame:0):({south:0,east:1,north:2,west:3}[facing]??0);
    const renderWidth=(visual.render_size_cells?.[0]||1)*tileSize,renderHeight=(visual.render_size_cells?.[1]||1)*tileSize;
    const x=position.x*tileSize+(tileSize-renderWidth)/2,y=(position.y+1)*tileSize-renderHeight;
    if(Array.isArray(visual.source_rect)){
     const [sx,sy,sw,sh]=visual.source_rect;
     ctx.drawImage(img,column*visual.frame_size+sx,visual.row*visual.frame_size+sy,sw,sh,x,y,renderWidth,renderHeight);
    }else ctx.drawImage(img,column*visual.frame_size,visual.row*visual.frame_size,visual.frame_size,visual.frame_size,x,y,renderWidth,renderHeight);
   }else if(Array.isArray(visual.source_size)&&Array.isArray(visual.render_size_cells)){
    const renderWidth=visual.render_size_cells[0]*tileSize,renderHeight=visual.render_size_cells[1]*tileSize;
    const x=position.x*tileSize+(tileSize-renderWidth)/2,y=(position.y+1)*tileSize-renderHeight;
    ctx.drawImage(img,0,0,visual.source_size[0],visual.source_size[1],x,y,renderWidth,renderHeight);
   }else if(Number.isInteger(visual.frame_width)&&Number.isInteger(visual.frame_height)){
    const scale=tileSize/16;ctx.drawImage(img,visual.frame*visual.frame_width,0,visual.frame_width,visual.frame_height,position.x*tileSize,position.y*tileSize-(visual.anchor_y||0)*scale,visual.frame_width*scale,visual.frame_height*scale);
   }
  }

  const hud=document.createElement('div');hud.className='world-hud';const region=document.createElement('span');region.className='world-region';const controls=document.createElement('div');
  for(const [label,action] of [['−',()=>{overview=false;zoom=Math.max(.5,zoom>=2?Math.floor(zoom)-1:zoom-.25)}],['+',()=>{overview=false;zoom=Math.min(5,Math.floor(zoom)+1)}],['Follow',()=>{overview=false;follow=true}],['Overview',()=>{overview=true;follow=false}]]){const b=document.createElement('button');b.textContent=label;b.type='button';b.onclick=action;controls.append(b)}hud.append(region,controls);container.append(hud);
  canvas.onpointerdown=e=>{overview=false;drag={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);follow=false};canvas.onpointermove=e=>{if(!drag)return;camera.x-=(e.clientX-drag.x)/zoom;camera.y-=(e.clientY-drag.y)/zoom;drag={x:e.clientX,y:e.clientY}};canvas.onpointerup=()=>drag=null;canvas.onpointercancel=()=>drag=null;
  canvas.onwheel=e=>{e.preventDefault();overview=false;zoom=Math.max(1,Math.min(5,zoom-Math.sign(e.deltaY))) };
  function update(s){
   const prior=state;connected=true;state=s;for(const object of s.environment_objects||[])loadVisual(object.visual);if(!s.world){container.classList.remove('topdown');return}container.classList.add('topdown');
   const mapUrl=s.world.map_url||'/assets/world/maps.json';if(mapUrl!==loadedMapUrl){loadMap(mapUrl);pose={...s.world};queue=[];segment=null;lastTick=s.tick}
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
     const tileSize=data.tile_size||16;const fit=Math.min((width-24)/(m.width*tileSize),(height-80)/(m.height*tileSize));
     zoom=fit<1?fit:Math.floor(fit);camera={x:m.width*tileSize/2,y:m.height*tileSize/2};
    }
    if(follow){
     const clamp=(v,size,view)=>size<=view?size/2:Math.max(view/2,Math.min(size-view/2,v));
     const tileSize=data.tile_size||16;camera.x=clamp(pose.x*tileSize+tileSize/2,m.width*tileSize,width/zoom);camera.y=clamp(pose.y*tileSize+tileSize/2,m.height*tileSize,height/zoom);
    }
    ctx.fillStyle='#192e2e';ctx.fillRect(0,0,width,height);ctx.save();ctx.translate(Math.round(width/2-camera.x*zoom),Math.round(height/2-camera.y*zoom));ctx.scale(zoom,zoom);
    if(mapImage.complete&&mapImage.naturalWidth){
     let terrain=terrainCache.get(pose.region);
     if(!terrain){
      const tileSize=data.tile_size||16;terrain=document.createElement('canvas');terrain.width=m.width*tileSize;terrain.height=m.height*tileSize;
      const terrainContext=terrain.getContext('2d');terrainContext.imageSmoothingEnabled=false;
      for(let y=0;y<m.height;y++)for(let x=0;x<m.width;x++){const tile=m.tiles[y*m.width+x];terrainContext.drawImage(mapImage,(tile%data.atlas_columns)*tileSize,Math.floor(tile/data.atlas_columns)*tileSize,tileSize,tileSize,x*tileSize,y*tileSize,tileSize,tileSize)}
      terrainCache.set(pose.region,terrain);
     }
     // Scale one continuous surface so fractional phone overview cannot expose tile seams.
     ctx.drawImage(terrain,0,0);
    }
    const things=(state.objects||[]).filter(o=>o.visible&&o.region===pose.region&&o.function!=='berry-plot').map(o=>({y:o.y+.75,object:o}));
    for(const building of data.scene_layout?.buildings||[])if((building.region||'MAP_LITTLEROOT_TOWN')===pose.region){
     const first=building.view_indices?.[0]||0,row=Math.floor(first/4),width=building.width,height=building.height;
     const visual={atlas_url:'/assets/interactive-art/v1/buildings.png',row,frame_size:128,
      render_size_cells:[width,height],rotation_degrees:building.rotation_degrees||0};
     things.push({y:building.y+height-.2,environment:{position:{region:pose.region,x:building.x+(width-1)/2,y:building.y+height-1},visual}});
    }
    for(const placement of data.scene_layout?.placements||[])if(placement.position.region===pose.region)
     things.push({y:placement.position.y+1,environment:placement});
    for(const object of state.environment_objects||[])if(object.position.region===pose.region)things.push({y:object.position.y+1,environment:object});
    things.push({y:pose.y+.75,actor:true});things.sort((a,b)=>a.y-b.y);
    const moving=connected&&state.running&&segment&&segment.from.region===segment.to.region&&(segment.from.x!==segment.to.x||segment.from.y!==segment.to.y);
    const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
    for(const thing of things){
     if(thing.actor){
      const tileSize=data.tile_size||16;const x=Math.round(pose.x*tileSize+tileSize/2),y=Math.round(pose.y*tileSize+tileSize*.75);ctx.fillStyle='#344b3438';ctx.fillRect(x-4,y-1,8,2);ctx.fillRect(x-3,y+1,6,1);
      const row={south:0,west:1,east:2,north:3}[pose.facing]??0;
      const expressive=!moving&&expression!=='idle'&&(!['learned','rehearse'].includes(expression)||now<expressionUntil);
      if(expressive){
       const clip=clips[expression];
       if(connected&&(state.running||now<expressionUntil)&&!reduced)expressionFrame=Math.floor((now-expressionStart)*clip.fps/1000)%4;
       const index=reduced?0:expressionFrame;if(!currentCharacter(pose.facing,index,x,y))sprite(clip.sheet,clip.row,index,x,y);
       canvas.dataset.clip=expression;canvas.dataset.frame=String(index);
      }else if(moving){
       const col=reduced?0:Math.floor(frame/140)%4;if(!currentCharacter(pose.facing,col,x,y))sprite('movement',row,col,x,y);canvas.dataset.clip='walk';canvas.dataset.frame=String(col);
      }else{
       const col=connected&&state.running&&!reduced?Math.floor(frame/350)%4:0;
       if(!currentCharacter(pose.facing,col,x,y)){if(pose.facing==='south')sprite('daily',0,col,x,y);else sprite('movement',row,0,x,y);}
       canvas.dataset.clip='idle';canvas.dataset.frame=String(pose.facing==='south'?col:0);
      }
      canvas.dataset.facing=pose.facing;canvas.dataset.walking=String(Boolean(moving));canvas.dataset.region=pose.region;canvas.dataset.x=pose.x.toFixed(3);canvas.dataset.y=pose.y.toFixed(3);
     }else if(thing.environment){
      const {position:p,visual:v}=thing.environment,tileSize=data.tile_size||16;
      if(v.underlay)drawVisual(v.underlay,p,tileSize);
      drawVisual(v,p,tileSize);
     }else{
      const tileSize=data.tile_size||16;const o=thing.object;
      const artRow=o.identity==='workshop-lantern'?0:o.identity==='workshop-stone'?2:null;
      if(artRow!==null){
       const asset='/assets/interactive-art/v1/directional-outdoor.png';loadVisual({atlas_url:asset});const img=environmentImages[asset];
       if(img?.complete&&img.naturalWidth){const facing=['south','east','north','west'][((Math.round((o.rotation_degrees||0)/90)%4)+4)%4],column={south:0,east:1,north:2,west:3}[facing];
        const renderWidth=(artRow===0?0.75:0.9)*tileSize,renderHeight=(artRow===0?1.35:0.7)*tileSize;
        ctx.drawImage(img,column*128,artRow*128,128,128,o.x*tileSize+(tileSize-renderWidth)/2,(o.y+1)*tileSize-renderHeight,renderWidth,renderHeight);
       }
      }else drawProp(o,o.x*tileSize+tileSize/2,o.y*tileSize+tileSize*.75);
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
