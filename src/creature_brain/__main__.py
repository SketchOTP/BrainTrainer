"""Run and inspect the standalone creature simulation without game binaries."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
from .simulation import Simulation, make_demo


def replay_html(frames, world, summary):
    payload = json.dumps({'frames':frames,'width':world.width,'height':world.height,
                          'summary':summary},allow_nan=False).replace('<','\\u003c')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital creature · simulation replay</title><style>
body{margin:0;background:#101820;color:#e1eced;font:16px system-ui}main{max-width:1120px;margin:30px auto;padding:0 20px}h1{font-size:27px;font-weight:550;margin-bottom:7px}.muted{color:#9ab3b7}canvas{width:100%;background:#172932;border:1px solid #35515b;border-radius:12px;margin:20px 0}button,input{accent-color:#70d4b4}button{background:#70d4b4;border:0;padding:9px 17px;border-radius:6px;color:#102e2b;cursor:pointer}input{width:65%;vertical-align:middle;margin:0 15px}#cards{display:flex;gap:15px;flex-wrap:wrap}.card{background:#1b303a;padding:18px;border-radius:10px;min-width:275px;flex:1}.bars{display:grid;grid-template-columns:90px 1fr 45px;gap:5px;font-size:13px}progress{width:100%;accent-color:#70d4b4}footer{color:#9ab3b7;font-size:13px;margin:25px 0}a{color:#70d4b4}</style>
<main><h1>Digital creature · simulation replay</h1><div class="muted">15 lobes · 29 tracts · genome-driven decisions · recorded body and world</div>
<canvas id="world" width="1080" height="520" aria-label="Recorded creature positions and resources"></canvas>
<button id="play">Play</button><input id="timeline" type="range" min="0" value="0" aria-label="Simulation frame"><span id="clock"></span><div id="cards" style="margin-top:20px"></div>
<footer>Recorded deterministic simulation. Circles are creatures; green resources are food, violet is a toy, blue is home, red is danger. Needs run from 0 to 1. Commands are teaching stimuli, not motor overrides. This research implementation is not qualified as native game parity or biological realism.</footer></main>
<script>const data='''+payload+''';
const canvas=document.getElementById('world'),ctx=canvas.getContext('2d'),slider=document.getElementById('timeline'),clock=document.getElementById('clock'),cards=document.getElementById('cards');
const names=['look','push','pull','deactivate','approach','retreat','get','drop','express','rest','left','right','eat','hit'];let playing=false;slider.max=Math.max(0,data.frames.length-1);
function draw(){const frame=data.frames[+slider.value];if(!frame)return;ctx.clearRect(0,0,1080,520);const sx=x=>30+x/data.width*1020,sy=y=>490-y/data.height*460;
ctx.strokeStyle='#24404a';for(let x=0;x<=data.width;x+=2){ctx.beginPath();ctx.moveTo(sx(x),25);ctx.lineTo(sx(x),495);ctx.stroke()}
for(const o of frame.objects){if(o.kind==='food'&&o.quantity<=0)continue;ctx.fillStyle=({food:'#70d4a4',toy:'#b393ef',home:'#71b9e8',danger:'#ec827b'})[o.kind]||'#a4bbc1';ctx.fillRect(sx(o.x)-6,sy(o.y)-6,12,12);ctx.font='12px system-ui';ctx.fillText(o.id+' '+(o.kind==='food'?o.quantity.toFixed(1):''),sx(o.x)+11,sy(o.y)+4)}
cards.replaceChildren();frame.creatures.forEach((c,i)=>{ctx.fillStyle=['#ffe08c','#f3a4c8','#95bfff','#b4dd99'][i%4];ctx.beginPath();ctx.arc(sx(c.x),sy(c.y),11,0,Math.PI*2);ctx.fill();ctx.font='13px system-ui';ctx.fillText(c.id,sx(c.x)+15,sy(c.y)-10);const card=document.createElement('div');card.className='card';const title=document.createElement('strong');title.textContent=c.id+' · '+c.sleep;card.append(title);const line=document.createElement('p');line.textContent=names[c.action]+' → '+(c.target||'no target')+' · '+c.outcome+(c.commanded?' · teaching':'');card.append(line);const bars=document.createElement('div');bars.className='bars';[[1,'Protein'],[2,'Starch'],[3,'Fat'],[6,'Fatigue'],[7,'Sleep'],[8,'Loneliness'],[10,'Fear'],[11,'Boredom']].forEach(([n,label])=>{const a=document.createElement('span'),b=document.createElement('progress'),v=document.createElement('span');a.textContent=label;b.max=1;b.value=c.drives[n];v.textContent=c.drives[n].toFixed(2);bars.append(a,b,v)});card.append(bars);const small=document.createElement('p');small.className='muted';small.textContent='Health '+c.health.toFixed(2)+' · migrations '+c.migrations+' · rehearsals '+c.instincts_processed;card.append(small);cards.append(card)});clock.textContent=frame.time.toFixed(2)+' s / '+data.frames.at(-1).time.toFixed(2)+' s'}
slider.oninput=draw;document.getElementById('play').onclick=()=>{playing=!playing;document.getElementById('play').textContent=playing?'Pause':'Play'};setInterval(()=>{if(playing){slider.value=(+slider.value+1)%data.frames.length;draw()}},100);draw();</script></html>'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--genome',type=Path,help='Normalized actual genome brain-program JSON')
    parser.add_argument('--physiology-genome',type=Path,help='Full matching genome JSON or dna3 file for biochemistry')
    parser.add_argument('--body',choices=('genome','simplified'),default='genome',help='Default genome; simplified is an explicit legacy comparison')
    parser.add_argument('--resume',type=Path,help='Resume a full simulation checkpoint')
    parser.add_argument('--steps',type=int,default=400)
    parser.add_argument('--seed',type=int,default=7)
    parser.add_argument('--creatures',type=int,default=2)
    parser.add_argument('--dt',type=float,default=.2)
    parser.add_argument('--timing',choices=('docking-nominal','legacy'),default='docking-nominal',help='Nominal: 50ms world ticks, creature update every fourth tick; legacy retains the earlier 1s biochemical tick')
    parser.add_argument('--scenario',choices=('autonomous','feeding','sleep','social'),default='autonomous')
    parser.add_argument('--output',type=Path,default=Path('runs/latest'))
    args=parser.parse_args()
    if not 1<=args.steps<=1_000_000: parser.error('--steps must be1..1000000')
    if args.resume and (args.genome or args.physiology_genome): parser.error('choose --resume or genome inputs')
    if args.resume and args.scenario!='autonomous': parser.error('resumed state cannot be changed by a scenario')
    genome=args.genome or Path(__file__).resolve().parents[2]/'research/docking-station-20261103/resources/chichi-brain-program.json'
    started=time.perf_counter()
    sim=Simulation.load(args.resume) if args.resume else make_demo(genome,seed=args.seed,count=args.creatures,dt=args.dt,rehearse=args.scenario!='sleep',body_model=args.body,physiology_genome=args.physiology_genome,timing_profile=args.timing)
    if not args.resume:
        for identity,c in sim.creatures.items():
            if args.scenario=='feeding':
                c.body.protein=c.body.starch=c.body.fat=.2
                sim.command(identity,action=12,category=11,seconds=60)
            elif args.scenario=='sleep':
                c.body.fatigue=.3;c.body.sleep_debt=.1;c.body.request_sleep()
            elif args.scenario=='social':
                sim.command(identity,action=1,category=36,seconds=60)
    args.output.mkdir(parents=True,exist_ok=True)
    frames=[]
    with (args.output/'trajectory.jsonl').open('w') as stream:
        for _ in range(args.steps):
            frame=sim.step(); stream.write(json.dumps(frame,allow_nan=False)+'\n')
            if len(frames)<2000: frames.append(frame)
            elif sim.steps%max(1,args.steps//2000)==0: frames.append(frame)
    summary=sim.summary()
    summary.update(scenario='resumed' if args.resume else args.scenario,
                   wall_seconds=time.perf_counter()-started,
                   timing='checkpoint-defined' if args.resume else args.timing,
                   qualifications={'genome':'actual normalized local Chichi genome',
                                   'controller':'decision-lobe only; no high-level fallback',
                                   'body':'checkpoint-defined' if args.resume else args.body,
                                   'world':'original simplified simulation',
                                   'native_parity':False,'biological_realism':False})
    sim.save(args.output/'checkpoint.json')
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    (args.output/'replay.html').write_text(replay_html(frames,sim.world,summary))
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
