'use strict';
// Presentation only. World position and motor decisions are supplied by the simulation.
function resolveHeading(previous,next){
 if(Number.isFinite(next.heading))return next.heading;
 if(previous){const dx=next.x-previous.x,dy=next.y-previous.y;if(Math.hypot(dx,dy)>1e-8)return Math.atan2(dy,dx);}
 return previous?.heading??0;
}
function interpolatePose(from,to,amount){
 const t=Math.max(0,Math.min(1,amount));
 const angle=Math.atan2(Math.sin(to.heading-from.heading),Math.cos(to.heading-from.heading));
 return {x:from.x+(to.x-from.x)*t,y:from.y+(to.y-from.y)*t,heading:from.heading+angle*t};
}
// A single bilinear ground projection maps the unchanged rectangular world
// across the ground plane of the original angled backdrop. No collision changes.
function projectPoint(x,y,width=20,height=12){
 const u=x/width,v=y/height;
 return [110+740*u-100*v+200*u*v,50+450*v+12*u*(1-v)];
}
function projectHeading(heading,x,y,width=20,height=12){
 const u=x/width,v=y/height,du=Math.cos(heading)/width,dv=Math.sin(heading)/height;
 return Math.atan2(12*(1-v)*du+(450-12*u)*dv,(740+200*v)*du+(-100+200*u)*dv);
}
function unprojectPoint(sx,sy,width=20,height=12){
 let u=(sx-110)/740,v=(sy-50)/450;
 for(let i=0;i<8;i++){
  const rx=sx-(110+740*u-100*v+200*u*v),ry=sy-(50+450*v+12*u*(1-v));
  const a=740+200*v,b=-100+200*u,c=12*(1-v),d=450-12*u,det=a*d-b*c;
  u+=(rx*d-b*ry)/det;v+=(a*ry-rx*c)/det;
 }
 return [u*width,v*height];
}
function directionFrame(heading,x=10,y=6,width=20,height=12){
 const angle=projectHeading(heading,x,y,width,height);
 return ((Math.round(angle/(Math.PI/8))%16)+16)%16;
}
function spriteView(direction){
 const d=((direction%16)+16)%16;
 if(d>=2&&d<=6)return {index:1,flip:false};
 if(d>=7&&d<=9)return {index:0,flip:false};
 if(d>=10&&d<=14)return {index:3,flip:d>=12};
 return {index:2,flip:false};
}
function perspectiveScale(y,height=12){return .9+.25*Math.max(0,Math.min(1,y/height));}
function creaturePlacement(x,y,width=20,height=12){
 const anchor=projectPoint(x,y,width,height),scale=1.35*perspectiveScale(y,height);
 return {anchor,scale,left:anchor[0]-32*scale,top:anchor[1]-65*scale,
         footY:anchor[1],shadowWidth:44*scale,shadowHeight:13*scale,depth:anchor[1]};
}
function depthOrder(a,b){return a.depth-b.depth;}
if(typeof module!=='undefined')module.exports={resolveHeading,interpolatePose,projectPoint,unprojectPoint,projectHeading,directionFrame,spriteView,depthOrder,perspectiveScale,creaturePlacement};
if(typeof document!=='undefined'){
let state=null,token=null,busy=false,refreshing=false,connected=true;
const $=id=>document.getElementById(id);
const canvas=$('world-canvas'),ctx=canvas.getContext('2d',{alpha:false});
const W=960,H=540,reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
let zoom=1,lastTick=null,fromPose=null,toPose=null,receivedAt=0,transitionMs=200,walking=false;
let animTime=0,lastPaint=0,selectedFeature=null,viewCamera={x:W/2,y:H/2};
const makeCanvas=(w,h)=>{const c=document.createElement('canvas');c.width=w;c.height=h;return c;};
const spriteCache=new Map();
const objectSpriteCache=new Map();
function objectSprite(rows){
 const key=rows.join('/');if(objectSpriteCache.has(key))return objectSpriteCache.get(key);
 const image=makeCanvas(12,12),g=image.getContext('2d');g.imageSmoothingEnabled=false;
 for(let y=0;y<12;y++)for(let x=0;x<12;x++){const pixel=rows[y][x];if(pixel!=='.'){g.fillStyle=state.world.visual_palette[pixel];g.fillRect(x,y,1,1);}}
 if(objectSpriteCache.size>256)objectSpriteCache.clear();objectSpriteCache.set(key,image);return image;
}
const backdrop=new Image();let backdropReady=false;
backdrop.onload=()=>{backdropReady=true;};
backdrop.referrerPolicy='no-referrer';
backdrop.onerror=()=>{$('notice').textContent='The scene artwork could not load. Your creature state is preserved.';};
backdrop.src='/habitat.png';
const mossSheet=new Image();let mossReady=false;
mossSheet.onload=()=>{mossReady=true;};mossSheet.src='/moss-animated-v1.png';
function animationRow(s){
 if(!s.alive)return 9;
 if(s.sleep!=='awake'||s.outcome==='resting'||s.outcome==='sleeping')return 5;
 if(s.outcome==='ate')return 3;
 if(s.outcome==='drank')return 4;
 if(s.outcome==='washed'||s.outcome==='splashed')return 8;
 if(s.outcome==='played')return 6;
 if(['foraged','discovered','picked-up','stored','decorated'].includes(s.outcome))return 7;
 if(s.action==='Retreating')return 2;
 if(s.pet.moving||s.outcome==='moved')return 1;
 if(['Pushing','Pulling','Expressing'].includes(s.action))return 6;
 if(Math.max(s.drives?.[6]??0,s.drives?.[7]??0)>.75)return 9;
 return 0;
}
function animationFrame(row,now){
 if(reduced)return row===5?3:0;
 const durations=[420,105,72,150,170,620,135,130,125,260];
 return row===5?2+Math.floor(now/durations[row])%4:Math.floor(now/durations[row])%8;
}
function animateCreatureCard(s,now){
 const avatar=$('moss-creature');if(!mossReady||!avatar)return;
 const row=animationRow(s),frame=animationFrame(row,now),cell=avatar.clientWidth||166;
 avatar.style.backgroundSize=`${cell*8}px ${cell*10}px`;
 avatar.style.backgroundPosition=`${-frame*cell}px ${-row*cell}px`;
 avatar.style.transform=directionFrame(toPose?.heading??s.pet.heading,s.pet.x,s.pet.y,s.world.width,s.world.height)>=8?'scaleX(-1)':'none';
 avatar.dataset.animation=['idle','walk','run','eat','drink','sleep','play','forage','wash','mood'][row];
 avatar.setAttribute('aria-label',s.name+' '+avatar.dataset.animation+' animation');
}
function rect(g,color,x,y,w,h){g.fillStyle=color;g.fillRect(Math.round(x),Math.round(y),Math.max(1,Math.round(w)),Math.max(1,Math.round(h)));}
function poly(g,color,points){
 // Scanline fill keeps every silhouette on the source pixel grid.
 const low=Math.ceil(Math.min(...points.map(p=>p[1]))),high=Math.floor(Math.max(...points.map(p=>p[1])));
 for(let y=low;y<=high;y++){const intersections=[];for(let i=0;i<points.length;i++){const a=points[i],b=points[(i+1)%points.length];if((a[1]<=y&&b[1]>y)||(b[1]<=y&&a[1]>y))intersections.push(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]));}intersections.sort((a,b)=>a-b);for(let i=0;i+1<intersections.length;i+=2)rect(g,color,Math.ceil(intersections[i]),y,Math.floor(intersections[i+1])-Math.ceil(intersections[i])+1,1);}
}
function pixelOval(g,color,x,y,w,h){for(let j=0;j<h;j++){const v=(j+.5-h/2)/(h/2),half=Math.sqrt(Math.max(0,1-v*v))*w/2;rect(g,color,x+w/2-half,y+j,Math.max(1,Math.floor(half*2)),1);}}
function hash(x,y,salt=0){let n=Math.imul(x+391,374761393)^Math.imul(y+163,668265263)^Math.imul(salt+7,1274126177);n=Math.imul(n^(n>>>13),1274126177);return (n^(n>>>16))>>>0;}
function mapPoint(x,y){return projectPoint(x,y,state.world.width,state.world.height);}
function spriteFor(direction,frame,sleeping,dead,eating,wet=0){
 const key=[direction,frame,sleeping,dead,eating,wet].join(':');if(spriteCache.has(key))return spriteCache.get(key);
 const image=makeCanvas(64,76),g=image.getContext('2d');g.imageSmoothingEnabled=false;
 const angle=direction*Math.PI/8,side=Math.cos(angle),front=Math.sin(angle);
 const step=[0,1,2,1,0,-1][frame%6],bob=sleeping?8:Math.abs(step)*.55+(eating?frame%2*2:0);
 const cx=32,hx=32+side*6,hy=24+front*2+bob;
 const rear=front<-.35,profile=Math.abs(side)>.8;
 const tailX=cx-side*20,tailY=48-front*7;
 function tail(){poly(g,'#293a34',[[cx,47],[tailX-3,tailY-3],[tailX-side*7,tailY+2],[tailX,tailY+7],[cx,54]]);poly(g,'#64704f',[[cx,48],[tailX,tailY],[tailX-side*5,tailY+3],[tailX,tailY+5],[cx,52]]);rect(g,'#94926b',tailX-1,tailY+1,3,2);}
 if(!rear)tail();
 // Back legs, then stocky torso with a weathered slate/moss carapace.
 const legY=sleeping?61:61;
 for(const [x,sign] of [[19,1],[39,-1]]){poly(g,'#293c34',[[x,49],[x+8,49],[x+9,legY+step*sign],[x-2,legY+step*sign],[x-2,57]]);rect(g,'#665f48',x-1,legY-3+step*sign,9,4);rect(g,'#a19772',x,legY+step*sign,2,1);rect(g,'#8d8463',x+4,legY+step*sign,2,1);}
 poly(g,'#263b33',[[20,27+bob],[43,27+bob],[50,39+bob],[49,54],[43,61],[20,61],[13,54],[13,39+bob]]);
 poly(g,'#51634b',[[21,28+bob],[42,28+bob],[47,38+bob],[47,52],[40,58],[21,58],[16,52],[16,39+bob]]);
 poly(g,'#74805a',[[23,29+bob],[39,28+bob],[44,36+bob],[42,46],[23,50],[18,43]]);
 poly(g,'#92976b',[[25,29+bob],[34,29+bob],[37,35+bob],[32,42],[23,43],[21,36]]);
 if(!rear){poly(g,'#7f7858',[[24,43],[40,43],[42,54],[36,59],[25,57],[22,51]]);rect(g,'#a1936c',26,47,9,3);rect(g,'#69694e',28,53,9,2);}
 else{poly(g,'#3d5143',[[24,33],[40,33],[44,46],[39,56],[26,58],[20,47]]);for(let i=0;i<5;i++){rect(g,'#84906a',28+i%2*3,34+i*4,6,2);rect(g,'#283f34',35+i%2,36+i*4,4,2);}}
 // Front arms change silhouette with facing rather than rotating the drawing.
 for(const sign of [-1,1]){const x=cx+sign*(profile?15:18),lift=sign*step;
  poly(g,sign<0?'#354c3c':'#465c42',[[x-3,36+bob],[x+4,37+bob],[x+5,51+lift],[x+1,56+lift],[x-5,53+lift]]);rect(g,'#8c8561',x-3,51+lift,7,3);rect(g,'#b0a47a',x-2,53+lift,2,1);}
 if(rear)tail();
 // Squared head, mineral brow and swept bark-like ears.
 const earLeft=hx-(profile?9:15),earRight=hx+(profile?9:15);
 for(const [ex,sign] of [[earLeft,-1],[earRight,1]]){poly(g,'#26382f',[[ex-sign*3,hy+3],[ex+sign*5,hy-13],[ex+sign*10,hy-9],[ex+sign*8,hy+7],[ex,hy+12]]);poly(g,'#5f6e4e',[[ex,hy+2],[ex+sign*5,hy-9],[ex+sign*7,hy-6],[ex+sign*5,hy+7]]);rect(g,'#989876',ex+sign*5,hy-8,2,3);}
 poly(g,'#263b31',[[hx-12,hy-5],[hx+11,hy-5],[hx+17,hy+3],[hx+15,hy+19],[hx+8,hy+24],[hx-10,hy+22],[hx-17,hy+13],[hx-17,hy+3]]);
 poly(g,'#6d7c55',[[hx-10,hy-5],[hx+9,hy-5],[hx+14,hy+3],[hx+12,hy+17],[hx+6,hy+21],[hx-9,hy+19],[hx-14,hy+11],[hx-14,hy+3]]);
 poly(g,'#93996b',[[hx-9,hy-5],[hx+7,hy-5],[hx+11,hy+1],[hx+4,hy+6],[hx-10,hy+5],[hx-12,hy+1]]);
 // Three worn crest plates replace ornamental facial decorations.
 for(let i=0;i<3;i++){const xx=hx-7+i*6;poly(g,i%2?'#6d8070':'#89917a',[[xx-2,hy-4],[xx,hy-10+i%2*2],[xx+4,hy-5],[xx+3,hy],[xx-2,hy+1]]);rect(g,'#b1b198',xx,hy-7+i%2*2,2,2);}
 if(!rear){
  const muzzleX=hx+side*7,muzzleY=hy+12;
  poly(g,'#998d65',[[muzzleX-7,muzzleY-2],[muzzleX+7,muzzleY-2],[muzzleX+8,muzzleY+4],[muzzleX+3,muzzleY+8],[muzzleX-6,muzzleY+6]]);
  rect(g,'#b0a37b',muzzleX-4,muzzleY-1,8,2);rect(g,'#344038',muzzleX+side*3-2,muzzleY+1,4,2);rect(g,'#5b5e47',muzzleX-3,muzzleY+5,6,1);
  const eyes=profile?[hx+side*8]:[hx-7+side*3,hx+7+side*3];
  for(const ex of eyes){rect(g,'#354333',ex-2,hy+5,5,4);rect(g,'#b6a762',ex-1,hy+6,3,sleeping||dead?1:2);if(!sleeping&&!dead){rect(g,'#252f2b',ex,hy+6,1,2);rect(g,'#d1c797',ex-1,hy+6,1,1);}rect(g,'#a0a16e',ex-3,hy+3,6,1);}
 }else{
  poly(g,'#556a4d',[[hx-10,hy+5],[hx+10,hy+5],[hx+11,hy+17],[hx+5,hy+21],[hx-8,hy+18]]);
  for(let i=0;i<5;i++){rect(g,i%2?'#89916a':'#3c5340',hx-7+i*3,hy+8+i%3*3,3,2);}
 }
 // Restrained pixel fur and scuffs give the larger sprite surface detail.
 for(let i=0;i<14;i++){const xx=19+hash(i,2)%26,yy=35+hash(i,8)%20;rect(g,i%3?'#566447':'#95946b',xx,yy,2,1);}
 if(wet>0){
  g.save();g.globalCompositeOperation='source-atop';g.fillStyle='rgba(30,65,69,'+(wet*.12)+')';g.fillRect(0,0,64,76);g.restore();
  for(let i=0;i<wet*2;i++){const x=18+hash(i,5)%27,y=40+hash(i,9)%20;rect(g,'#728d87',x,y,1,3);rect(g,'#a4b6a6',x,y,1,1);}
 }
 if(spriteCache.size>1500)spriteCache.clear();spriteCache.set(key,image);return image;
}
function drawObject(g,o){
 const [px,py]=mapPoint(o.x,o.y),scale=perspectiveScale(o.y,state.world.height);g.save();g.translate(Math.round(px),Math.round(py));g.scale(scale,scale);
 if(o.quantity<=0&&o.kind==='food')g.globalAlpha=.35;
 pixelOval(g,'#2b3829',-13,-2,28,10);
 if(o.visual){g.drawImage(objectSprite(o.visual),-12,-24,24,24);g.restore();return;}
 if(o.kind==='home'){
  // This movable map marker is the actual simulated home; the painted shed is scenery.
  poly(g,'#3e4438',[[-22,-8],[0,-17],[22,-8],[22,3],[0,12],[-22,3]]);
  poly(g,'#7d7858',[[-22,-8],[0,-17],[22,-8],[0,1]]);poly(g,'#5b6045',[[-22,-8],[0,1],[0,12],[-22,3]]);poly(g,'#424d39',[[0,1],[22,-8],[22,3],[0,12]]);
  pixelOval(g,'#a19060',-13,-10,28,13);pixelOval(g,'#655f42',-10,-8,22,10);for(let i=0;i<13;i++){const x=-9+hash(i,4)%19,y=-7+hash(i,2)%9;rect(g,i%2?'#aa9560':'#88794f',x,y,4,1);}
  rect(g,'#5b503d',16,-22,3,18);rect(g,'#b5a77b',12,-22,11,7);rect(g,'#59614a',14,-20,7,2);
 }else if(o.kind==='toy'){
  rect(g,'#493b2d',-9,-15,18,16);rect(g,'#9b7646',-9,-16,18,12);rect(g,'#c2a06a',-7,-16,14,3);rect(g,'#62563b',-6,-12,12,7);rect(g,'#728c78',-4,-11,8,5);rect(g,'#a6b29b',-3,-11,5,1);rect(g,'#ae8c55',-7,-3,14,3);rect(g,'#464e3d',-3,-9,6,2);
 }else{
  rect(g,'#59452e',-11,-6,23,9);pixelOval(g,'#9c8053',-12,-12,25,12);pixelOval(g,'#463e2d',-9,-10,19,8);rect(g,'#bd9c62',-10,-11,21,2);rect(g,'#786243',-10,-2,21,3);
  if(o.quantity>0)for(let i=0;i<12;i++){const n=hash(i,o.category),x=-7+n%15,y=-9+(n>>>5)%6;rect(g,o.category===8?['#615537','#97844b','#84743c'][i%3]:['#a88646','#c0a064','#7f8c51'][i%3],x,y,3,2);}
 }
 g.restore();
}
function drawCreature(g,p,now){
 const [px,py]=mapPoint(p.x,p.y),sleeping=state.sleep!=='awake',dead=!state.alive;
 const moving=walking&&!state.paused&&connected&&!sleeping&&!dead&&now-receivedAt<transitionMs+state.dt*1000;
 const row=animationRow(state),frame=animationFrame(row,animTime);
 const direction=directionFrame(p.heading,p.x,p.y,state.world.width,state.world.height);
 const wet=Math.min(4,Math.round((state.habitat?.creature?.wetness??0)*4));
 const placement=creaturePlacement(p.x,p.y,state.world.width,state.world.height),scale=placement.scale;
 pixelOval(g,'#172026',px-23*scale,py-4*scale,46*scale,13*scale);
 g.save();if(dead)g.globalAlpha=.65;
 if(mossReady){
  const flip=direction>=8;
  const bob=moving?Math.abs(Math.sin(animTime/130))*1.2:0;
  const height=(sleeping?72:78)*scale-bob,width=height;
  g.translate(Math.round(px),Math.round(py-bob));
  if(flip)g.scale(-1,1);
  g.imageSmoothingEnabled=false;
  g.drawImage(mossSheet,frame*128,row*128,128,128,Math.round(-width/2),Math.round(-height),Math.round(width),Math.round(height));
 }else{
  const image=spriteFor(direction,frame,sleeping,dead,state.outcome==='ate',wet);
  g.drawImage(image,Math.round(placement.left),Math.round(placement.top),Math.round(64*scale),Math.round(76*scale));
 }
 g.restore();
 if(mossReady&&wet>0){for(let i=0;i<wet*2;i++){const x=px-20+hash(i,5)%40,y=py-20-hash(i,9)%32;rect(g,'#8eaaa0',x,y,1,3);}}
 if(sleeping){const n=Math.floor(animTime/900)%3;g.fillStyle='#b2baa2';g.font='8px monospace';g.fillText(n===0?'z':n===1?'z z':'z z z',Math.round(px)+22,Math.round(py)-61-n*2);}
 if(state.carrying){const held=state.objects.find(o=>o.id===state.carrying);const x=px+Math.cos(direction*Math.PI/8)*18-5,y=py-31+Math.sin(direction*Math.PI/8)*5;if(held?.visual)g.drawImage(objectSprite(held.visual),x,y,12,12);else rect(g,'#aa8d5b',x,y,7,5);}
}
function foreground(g,cameraX,cameraY){
 // Foreground branches sit outside the mapped clearing and move slightly
 // faster than its ground when the camera follows a zoomed creature.
 const dx=(W/2-cameraX)*.08,dy=(H/2-cameraY)*.08;
 g.save();g.translate(dx,dy);
 for(const side of [-1,1]){const x=side<0?0:W;poly(g,'#172b24',[[x,H],[x,H-90],[x-side*38,H-62],[x-side*79,H-22],[x-side*112,H]]);for(let i=0;i<18;i++){const xx=x-side*(12+i*5),yy=H-8-i%5*11;poly(g,i%3?'#2c4430':'#4c5e38',[[xx,yy],[xx-side*18,yy-12],[xx-side*8,yy-14],[xx+side*5,yy-3]]);}}
 g.restore();
}
function drawInterior(g){
 if(!state.habitat?.creature?.inside)return;
 const home=state.habitat.features.find(f=>f.kind==='shelter');if(!home)return;
 const [x,y]=mapPoint(home.x,home.y);g.save();g.translate(Math.round(x),Math.round(y));
 // Cutaway replaces the painted roof only while actual inside state is true.
 poly(g,'#27372b',[[-26,-50],[48,-70],[93,-45],[15,-20]]);
 poly(g,'#61543a',[[-26,-49],[15,-20],[15,19],[-26,-10]]);
 poly(g,'#3e3d2c',[[15,-20],[93,-45],[93,-9],[15,19]]);
 for(let i=0;i<7;i++)poly(g,i%2?'#796344':'#8c724b',[[-24+i*10,-10+i*4],[46+i*6,-31+i*4],[53+i*6,-27+i*4],[-17+i*10,-6+i*4]]);
 rect(g,'#332f23',-23,-50,4,40);rect(g,'#51432e',12,-22,4,41);rect(g,'#ae8a4a',-18,-42,5,8);rect(g,'#d1b56e',-17,-41,3,4);
 pixelOval(g,'#706447',9,-2,31,13);pixelOval(g,'#aa9866',12,-2,25,9);pixelOval(g,'#8a7a50',16,0,17,6);
 const stored=state.habitat.storage?.[home.id]??[];
 for(let i=0;i<Math.min(4,stored.length);i++){rect(g,'#4e3d2a',54+i%2*11,-22+Math.floor(i/2)*8,10,10);rect(g,'#9b7848',55+i%2*11,-22+Math.floor(i/2)*8,8,2);rect(g,'#6f5937',58+i%2*11,-20+Math.floor(i/2)*8,1,7);}
 const placed=state.habitat.decor?.[home.id]??[];
 for(let i=0;i<Math.min(5,placed.length);i++){const item=state.objects.find(o=>o.id===placed[i]),x=26+i*8;rect(g,'#413c2b',x,-18,7,3);rect(g,item?.kind==='food'?'#b39559':'#82937d',x+1,-23,5,5);rect(g,'#c1b382',x+2,-23,2,1);}
 g.restore();
}
function drawFeatureMarkers(g){
 if(!state.habitat)return;
 for(const f of state.habitat.features){const [x,y]=mapPoint(f.x,f.y),selected=f.id===selectedFeature;
  g.save();g.globalAlpha=selected?.95:.65;
  poly(g,selected?'#d1bb79':'#809578',[[x,y+5],[x+4,y+7],[x,y+9],[x-4,y+7]]);
  if(selected){g.strokeStyle='#c6b77a';g.strokeRect(Math.round(x)-10,Math.round(y)+1,20,11);}
  g.restore();
 }
}
function drawWaterMotion(g){
 const water=state.habitat?.features?.find(f=>f.kind==='water');if(!water)return;
 const [x,y]=mapPoint(water.x,water.y),phase=animTime/120;
 for(let i=0;i<13;i++){const xx=x-33+(i*7+phase)%68,yy=y-7+i%4*4;rect(g,i%3?'#86a6a1':'#c0c6ad',xx,yy,3+i%4,1);}
}
function selectFeature(id){selectedFeature=id;$('habitat-panel').open=true;renderHabitat(state);}
function renderHabitat(s){
 const habitat=s.habitat,panel=$('habitat-panel');if(!panel)return;
 panel.hidden=!habitat;if(!habitat)return;
 const physical=habitat.creature??{};
 $('environment-status').textContent=(physical.inside?'INSIDE SHELTER':String(physical.location??'clearing').replaceAll('-',' ').toUpperCase())+' · WET '+Math.round((physical.wetness??0)*100)+'%';
 const buttons=habitat.features.map(f=>{const button=document.createElement('button');button.textContent=f.label;button.className=f.id===selectedFeature?'selected':'';button.setAttribute('aria-pressed',String(f.id===selectedFeature));button.addEventListener('click',()=>selectFeature(f.id));return button;});$('places').replaceChildren(...buttons);
 const feature=habitat.features.find(f=>f.id===selectedFeature);
 $('feature-title').textContent=feature?.label??'Choose a place to explore';
 $('feature-detail').textContent=feature?'Offer a cue. Its brain decides whether and how to respond.':'Select a marker in the scene or a place above. Exploration does not force movement.';
 $('feature-actions').replaceChildren(...(feature?.cues??[]).map(cue=>{const button=document.createElement('button');button.textContent=cue.label;button.disabled=!s.alive||!!s.error;button.addEventListener('click',()=>act({action:'feature',feature:feature.id,cue:cue.id}));return button;}));
 const details=[];
 if(physical.inside)details.push('Inside the shelter');
 if(physical.elevation>0)details.push('Elevation '+Number(physical.elevation).toFixed(1));
 details.push('Cleanliness '+Math.round((physical.cleanliness??0)*100)+'%');
 details.push('Water consumed '+Number(physical.water_intake??0).toFixed(2));
 if(feature?.kind==='bush'){const forage=habitat.forage?.[feature.id];if(forage)details.push('Forage '+Number(forage.quantity).toFixed(1)+' / '+Number(forage.capacity).toFixed(1)+' · discoveries '+forage.discoveries);}
 const shelter=feature?.kind==='shelter'?feature.id:physical.shelter;
 if(shelter){const stored=habitat.storage?.[shelter]??[],decor=habitat.decor?.[shelter]??[];details.push('Stored: '+(stored.length?stored.join(', '):'empty'));details.push('Placed inside: '+(decor.length?decor.join(', '):'none'));}
 $('model-note').textContent='A digital creature running inside a local computer simulation. The 15-lobe genome brain receives body signals and chooses actions; the world provides resource locations and physical routes. Survival-resource cues are a separate host adaptation, not a recovered brain feature. Marked stations have interactive behavior; background scenery outside them is decorative. Closing saves and suspends Moss.';
 $('feature-state').replaceChildren(...details.map(text=>{const row=document.createElement('li');row.textContent=text;return row;}));
}
canvas.addEventListener('click',event=>{
 if(!state?.habitat)return;
 const bounds=canvas.getBoundingClientRect(),scale=Math.min(bounds.width/W,bounds.height/H);
 const mx=(event.clientX-bounds.left-(bounds.width-W*scale)/2)/scale,my=(event.clientY-bounds.top-(bounds.height-H*scale)/2)/scale;
 const point=[(mx-W/2)/zoom+viewCamera.x,(my-H/2)/zoom+viewCamera.y];
 let closest=null,distance=45;
 for(const feature of state.habitat.features){const p=mapPoint(feature.x,feature.y),d=Math.hypot(point[0]-p[0],point[1]-p[1]);if(d<distance){closest=feature;distance=d;}}
 if(closest)selectFeature(closest.id);
});
function viewPose(now){if(!toPose)return null;return interpolatePose(fromPose,toPose,reduced?1:(now-receivedAt)/transitionMs);}
function paint(now){
 const elapsed=lastPaint?Math.min(100,now-lastPaint):0;lastPaint=now;
 if(state&&!state.paused&&connected&&!reduced)animTime+=elapsed;
 if(state)animateCreatureCard(state,animTime);
 ctx.imageSmoothingEnabled=false;ctx.fillStyle='#152720';ctx.fillRect(0,0,W,H);
 if(state){
  const p=viewPose(now);let cameraX=W/2,cameraY=H/2;
  if(zoom>1){const [x,y]=mapPoint(p.x,p.y);cameraX=Math.max(W/(2*zoom),Math.min(W-W/(2*zoom),x));cameraY=Math.max(H/(2*zoom),Math.min(H-H/(2*zoom),y-25));}
  viewCamera={x:cameraX,y:cameraY};
  ctx.save();ctx.translate(W/2,H/2);ctx.scale(zoom,zoom);ctx.translate(-cameraX,-cameraY);
  if(backdropReady){
   ctx.drawImage(backdrop,0,0,W,H);
   // The distant virtual horizon has a slower camera response than the floor.
   if(zoom>1)ctx.drawImage(backdrop,0,0,backdrop.width,backdrop.height*.14,(cameraX-W/2)*.025,(cameraY-H/2)*.025,W,H*.14);
   // Small water highlights stay in the painted stream, below the mapped ground.
   const phase=Math.floor(animTime/450);for(let i=0;i<10;i++){const x=210+hash(i,5)%510,y=479+hash(i,7)%42;if((phase+i)%4===0)rect(ctx,'#9baf9a',x,y,3+i%3,1);}
  }
  drawInterior(ctx);drawFeatureMarkers(ctx);
  const entities=state.objects.filter(o=>!o.holder&&!o.stored_in).map(o=>({depth:mapPoint(o.x,o.y)[1],object:o}));entities.push({depth:mapPoint(p.x,p.y)[1],pet:true});entities.sort(depthOrder);
  for(const e of entities){if(e.pet)drawCreature(ctx,p,now);else drawObject(ctx,e.object);}
  drawWaterMotion(ctx);foreground(ctx,cameraX,cameraY);ctx.restore();
 }
 requestAnimationFrame(paint);
}
function acceptPose(s){
 const now=performance.now(),heading=resolveHeading(toPose,s.pet),next={x:s.pet.x,y:s.pet.y,heading};
 // A paused or ended body is rendered exactly at its current reported position.
 if(!toPose||s.paused||!s.alive){fromPose=next;toPose=next;receivedAt=now;walking=false;}
 else if(s.step!==lastTick){
  const previous=toPose;fromPose=viewPose(now)||next;toPose=next;receivedAt=now;
  transitionMs=Math.max(80,Math.min(350,(s.step-(lastTick??s.step-1))*s.dt*1000));
  walking=Math.hypot(next.x-previous.x,next.y-previous.y)>1e-7;
 }
 lastTick=s.step;
}
function render(s){
 acceptPose(s);state=s;if(s.control_token)token=s.control_token;
 $('name').textContent=s.name;document.title=s.name+' · creature brain';
 $('connection').textContent=s.error?'Needs attention':s.paused?'Paused':s.clock_lag>.1?'Running slowly':'Brain active';
 $('status-dot').style.background=s.error?'#b87862':s.paused?'#b7ab87':'#71916a';
 $('pause').textContent=s.paused?'Resume':'Pause';$('pause').disabled=!s.alive||!!s.error;
 const destination=s.intention&&s.target===s.intention.target?s.habitat?.features?.find(f=>f.id===s.target)?.label:null;
 const movement=destination?(s.action==='Retreating'?'Moving away from '+destination.toLowerCase():s.action==='Going left'||s.action==='Going right'?'Exploring computer space':'Heading toward '+destination.toLowerCase()):'Moving through computer space';
 $('activity').textContent=!s.alive?'Life has ended · final state saved':s.error?s.error:s.sleep!=='awake'?'Resting · '+s.sleep.toUpperCase():s.paused?'Brain paused':s.habitat_event||({moved:movement,ate:'Eating',played:'Playing',resting:'Resting',looked:'Looking around','picked-up':'Picked something up',dropped:'Dropped something',idle:'Observing'})[s.outcome]||s.action+' · '+s.outcome.replaceAll('-',' ');
 const avatar=$('moss-creature');avatar.classList.toggle('dead',!s.alive);
 const seconds=Math.floor(s.time);$('clock').textContent=Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0')+' simulated';
 const degrees=((toPose.heading*180/Math.PI)%360+360)%360;
 $('coordinates').textContent=s.pet.x.toFixed(1)+' / '+s.pet.y.toFixed(1)+' · '+Math.round(degrees)+'°';
 $('world-position').textContent=s.pet.x.toFixed(1)+' / '+s.pet.y.toFixed(1)+' · '+Math.round(degrees)+'°';
 canvas.setAttribute('aria-label',s.name+' in an angled digital computer world, at '+s.pet.x.toFixed(1)+', '+s.pet.y.toFixed(1)+', facing '+Math.round(degrees)+' world degrees clockwise from east. '+$('activity').textContent+'.');
 const d=s.drives,m=s.body_metrics||{},resources=m.resources||{};
 const hunger=Math.max(...d.slice(1,4)),sleeping=m.sleep_state&&m.sleep_state!=='awake';
 const needs=[
  ['Food signal',hunger,`Protein ${Math.round(d[1]*100)}% · starch ${Math.round(d[2]*100)}% · fat ${Math.round(d[3]*100)}%`],
  ['Tired',d[6],`Sleepiness ${Math.round(d[7]*100)}% · ${sleeping?'currently '+m.sleep_state:'currently awake'}`],
  ['Thirst',1-(m.water_reserve??1),`Water reserve ${Math.round((m.water_reserve??1)*100)}%`],
  ['Company signal',d[8],resources.companion?`Companion nearby: ${resources.companion.distance} world units`:'No companion exists in this world instance'],
  ['Energy need',1-(m.energy_reserve??1),`Energy reserve ${Math.round((m.energy_reserve??1)*100)}% · ATP ${Math.round((m.atp??1)*100)}%`],
  ['Comfort signals',Math.max(d[0],d[4],d[5],d[10]),`Cold ${Math.round(d[4]*100)}% · heat ${Math.round(d[5]*100)}%`]
 ];
 $('needs').replaceChildren(...needs.map(([name,value,detail])=>{const e=document.createElement('div');e.className='need';const label=document.createElement('span');label.textContent=name;const track=document.createElement('div');track.className='track';track.setAttribute('role','meter');track.setAttribute('aria-label',name);track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax','100');track.setAttribute('aria-valuenow',Math.round(value*100));const fill=document.createElement('div');fill.className='fill';fill.style.width=Math.max(0,Math.min(100,value*100))+'%';track.append(fill);const level=document.createElement('small');level.textContent=value>.65?'HIGH':value>.3?'MID':'LOW';const note=document.createElement('span');note.className='need-detail';note.textContent=detail;e.append(label,track,level,note);return e;}));
 const resourceLine=(label,item,count,empty)=>item?`${label}: ${item.label} · ${item.distance} units away${count===undefined?'':` · ${count} available`}`:`${label}: ${empty}`;
 const oldCue=s.last_survival_cue;
 const survivalCueText=s.intention?.source==='survival-affordance'?`Current survival cue: ${s.intention.need} → ${s.target?.replaceAll('-',' ')||'resource'}. This cue points; the brain still chooses its action.`:oldCue?`Most recent survival cue: ${oldCue.need} → ${oldCue.target.replaceAll('-',' ')} at ${(Number(oldCue.time)/3600).toFixed(2)} simulated hours.`:'No survival resource cue has been recorded yet.';
 $('resource-map').replaceChildren(...[
  resourceLine('Food',resources.food,resources.food_count,resources.foraging?'no prepared food; forage '+resources.foraging.label:'no visible food or forage'),
  resourceLine('Foraging',resources.foraging,resources.foraging_count,'no visible bushes'),
  resourceLine('Water',resources.water,undefined,'no water source in this instance'),
  resourceLine('Rest',resources.shelter,undefined,'no shelter in this instance'),
  resources.companion?resourceLine('Companion',resources.companion,undefined,'none'):'Companion: none present; social need cannot be met here',
  'Comfort: temperature and pain signals are tracked; shelter and water do not yet have a verified comfort-relief effect.',
  survivalCueText
 ].map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));
 $('events').replaceChildren(...s.events.slice().reverse().map(message=>{const e=document.createElement('li');e.textContent=message;return e;}));
 const memory=s.memory;
 $('mode-label').textContent=memory?.mode==='learned'?'LEARNING FROM EXPERIENCE':'GUIDED EXPLORATION';
 $('memory-count').textContent=memory?String(memory.retained):'0';
 $('memory-summary').textContent=memory?`${memory.observations} recorded experiences · ${memory.retained} recent memories · ${memory.visual_examples??0} learned object views`:'Experiences are loading.';
 const progress=s.progress||{};
 $('progress-strip').replaceChildren(...[
  ['Brain ticks',progress.brain_ticks??0],['Experiences',memory?.observations??0],
  ['Associations',memory?.learned_associations??0],['Places used',new Set((s.journal||[]).map(row=>row.target).filter(Boolean)).size]
 ].map(([label,value])=>{const item=document.createElement('div');item.className='progress-metric';item.innerHTML='<strong></strong><span></span>';item.querySelector('strong').textContent=Number(value).toLocaleString();item.querySelector('span').textContent=label;return item;}));
 const actionLabel=s.action||'Observing',targetLabel=s.habitat?.features?.find(f=>f.id===s.target)?.label||s.target?.replaceAll('-',' ')||'no target';
 $('decision-now').textContent=`${actionLabel} · ${targetLabel} · ${String(s.outcome||'ready').replaceAll('-',' ')}${s.intention?.source==='survival-affordance'?' · '+s.intention.need+' cue':''}`;
 const research=s.research;
 if(research){
  const benchmark=research.benchmark;
  $('research-status').textContent=research.status==='implemented-and-tested'
    ?`Last candidate: ${research.tests_passed??'unknown'} tests passed; not promoted.`
    :`Last cycle: ${String(research.status||'unknown').replaceAll('-',' ')}.`;
  $('research-result').textContent=benchmark
    ?`${benchmark.completed_seeds}/${benchmark.completed_seeds+benchmark.failed_seeds} trials completed · ${benchmark.zero_exposure_seeds} had no learning exposure · mean retained-memory difference ${Number(benchmark.mean_eating_difference).toFixed(1)} eating events. Preliminary; no reliable improvement established.`
    :'No paired capability benchmark is recorded in the latest cycle.';
 }else{$('research-status').textContent='No Codex capability cycle has completed yet.';$('research-result').textContent='';}
 const activityRows=(s.journal||[]).slice(-9).reverse();
 const activityItem=row=>{const li=document.createElement('li');const time=document.createElement('time');time.textContent=(Number(row.time)/3600).toFixed(2)+'h';const text=document.createElement('span');text.textContent=row.text;li.append(time,text);return li;};
 $('activity-log').replaceChildren(...activityRows.map(activityItem));
 $('activity-glance').replaceChildren(...activityRows.slice(0,3).map(activityItem));
 $('ability-status').replaceChildren(...[
  ['Explore and move','available'],['Eat, drink and sleep','available'],['Use water and shelter','available'],
  ['Remember outcomes','partial'],['Grow through life stages','not built'],['Build and craft','not built'],['Choose learning goals','not built']
 ].map(([label,status])=>{const li=document.createElement('li');li.className='ability '+status;li.textContent=label;return li;}));
 if(memory&&document.activeElement!==$('learning-mode'))$('learning-mode').value=memory.mode;
 $('memories').replaceChildren(...(memory?.recent||[]).slice().reverse().map(record=>{const e=document.createElement('li');const place=s.habitat?.features?.find(f=>f.id===record.target)?.label||record.target.replaceAll('-',' ');e.textContent=record.outcome.replaceAll('-',' ')+(['resting','dropped'].includes(record.outcome)?'':' · '+place);return e;}));
 $('saved').textContent=s.saved?'Saved locally at '+s.saved+'.':'Saves locally every 15 seconds and when closed.';
 document.querySelectorAll('[data-action]').forEach(e=>e.disabled=!s.alive||!!s.error);
 renderHabitat(s);
 if(document.activeElement!==$('pet-name'))$('pet-name').value=s.name;
}
function setZoom(value){zoom=Math.max(1,Math.min(2.5,value));$('zoom-label').textContent=Number(zoom.toFixed(1))+'×';$('zoom-out').disabled=zoom===1;$('zoom-in').disabled=zoom===2.5;}
$('zoom-out').addEventListener('click',()=>setZoom(zoom-.5));$('zoom-in').addEventListener('click',()=>setZoom(zoom+.5));$('zoom-reset').addEventListener('click',()=>setZoom(1));
canvas.addEventListener('keydown',e=>{if(e.key==='+'||e.key==='='){setZoom(zoom+.5);e.preventDefault();}else if(e.key==='-'){setZoom(zoom-.5);e.preventDefault();}else if(e.key==='0'){setZoom(1);e.preventDefault();}});
async function refresh(){if(refreshing)return;refreshing=true;try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw Error('Could not read habitat.');connected=true;render(await r.json());}catch(e){connected=false;walking=false;$('connection').textContent='Disconnected · world stops when server closes';$('status-dot').style.background='#b87862';}finally{refreshing=false;}}
async function act(data){if(busy||!token)return;busy=true;try{const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json','X-Pet-Token':token},body:JSON.stringify(data)});const s=await r.json();if(!r.ok)throw Error(s.error||'Action failed.');render(s);$('notice').textContent=data.action==='save'?'Checkpoint saved.':s.events[s.events.length-1]||'';}catch(e){$('notice').textContent=e.message;}finally{busy=false;}}
document.querySelectorAll('[data-action]').forEach(e=>e.addEventListener('click',()=>act({action:e.dataset.action,food:e.dataset.food})));
$('pause').addEventListener('click',()=>state&&act({action:'pause',paused:!state.paused}));$('save').addEventListener('click',()=>act({action:'save'}));
$('learning-mode').addEventListener('change',e=>act({action:'autonomy',mode:e.target.value}));
$('rename').addEventListener('submit',e=>{e.preventDefault();act({action:'rename',name:$('pet-name').value});});
setZoom(1);refresh();setInterval(refresh,200);requestAnimationFrame(paint);
}
