// ── Constants ─────────────────────────────────────────────────────────────────
const CLOSE_THR = 15, GRID = 16;
const PALETTES = [
  {name:"Ink",       bg:"#f8f8f8",icon:"#1a1a1a",acc:"#e63946"},
  {name:"Blueprint", bg:"#dceefb",icon:"#1d3557",acc:"#457b9d"},
  {name:"Forest",    bg:"#edf7ee",icon:"#1b4332",acc:"#52b788"},
  {name:"Ember",     bg:"#fff3e0",icon:"#7f2e00",acc:"#ff6d00"},
  {name:"Lavender",  bg:"#f3e8ff",icon:"#4a148c",acc:"#9c27b0"},
  {name:"Slate",     bg:"#eceff1",icon:"#263238",acc:"#00bcd4"},
  {name:"Rose",      bg:"#fce4ec",icon:"#880e4f",acc:"#e91e63"},
  {name:"Sage",      bg:"#f1f8e9",icon:"#2e4a1e",acc:"#7cb342"},
  {name:"Midnight",  bg:"#0d1117",icon:"#e6edf3",acc:"#58a6ff"},
  {name:"Sand",      bg:"#fdf6e3",icon:"#4a3728",acc:"#d4a853"},
];
const FONTS = ["Arial","Arial Rounded MT Bold","Georgia","Times New Roman",
  "Courier New","Verdana","Helvetica Neue","Trebuchet MS","Impact","Comic Sans MS"];

// ── State ─────────────────────────────────────────────────────────────────────
const S = {
  shapes:[], tool:'line', mode:'draw',
  strokeWidth:10, strokeColor:'#1a1a1a', defaultCornerRadius:0,
  selected:[], hover:null,
  isDrawing:false, startPos:{x:0,y:0}, curPos:{x:0,y:0},
  pathPoints:[], snapEp:null,
  undoStack:[], redoStack:[],
  bgColor:'#f8f8f8', showBackground:true, gridEnabled:true,
  snapEnabled:true, gridSnapEnabled:true,
  textFontFamily:'Arial Rounded MT Bold', textFontSize:24,
  palette:PALETTES[0],
  canvasW:512, canvasH:512, zoom:1, dirty:false,
  // interaction
  moving:[], moveStart:{x:0,y:0}, moveStartSnap:{x:0,y:0}, moveOrigins:[],
  rotating:null, rotAngle:0,
  curveDrag:null,
  textResize:null, textResizeStart:{x:0,y:0}, textResizeStartSz:24, textResizeH:1,
  cursor:{x:0,y:0},
};

// ── Canvas ────────────────────────────────────────────────────────────────────
const cv = document.getElementById('canvas');
const cx = cv.getContext('2d');

function initCanvas() {
  cv.width=S.canvasW; cv.height=S.canvasH;
  cv.style.width  = Math.round(S.canvasW * S.zoom) + 'px';
  cv.style.height = Math.round(S.canvasH * S.zoom) + 'px';
  redraw();
}

function canvasPos(e) {
  const r = cv.getBoundingClientRect();
  return { x:(e.clientX-r.left)*(S.canvasW/r.width), y:(e.clientY-r.top)*(S.canvasH/r.height) };
}

// ── Undo/Redo ─────────────────────────────────────────────────────────────────
function saveState() {
  S.dirty = true;
  S.undoStack.push(JSON.parse(JSON.stringify(S.shapes)));
  if (S.undoStack.length > 50) S.undoStack.shift();
  S.redoStack = [];
}
function undo() {
  if (!S.undoStack.length) return;
  S.dirty = true;
  S.redoStack.push(JSON.parse(JSON.stringify(S.shapes)));
  S.shapes = S.undoStack.pop(); S.selected = []; selWidget(); redraw();
}
function redo() {
  if (!S.redoStack.length) return;
  S.dirty = true;
  S.undoStack.push(JSON.parse(JSON.stringify(S.shapes)));
  S.shapes = S.redoStack.pop(); S.selected = []; selWidget(); redraw();
}

// ── Snap helpers ──────────────────────────────────────────────────────────────
const snapGrid = p => ({ x:Math.round(p.x/GRID)*GRID, y:Math.round(p.y/GRID)*GRID });
const snapRot  = a => Math.round(a/22.5)*22.5;
function snapAngle(raw) {
  const dx=raw.x-S.startPos.x, dy=raw.y-S.startPos.y, d=Math.hypot(dx,dy);
  if (!d) return raw;
  const a = Math.round(Math.atan2(dy,dx)*180/Math.PI/22.5)*22.5*Math.PI/180;
  return { x:Math.round(S.startPos.x+d*Math.cos(a)), y:Math.round(S.startPos.y+d*Math.sin(a)) };
}
function allEndpoints() {
  const r=[];
  for (const s of S.shapes) {
    if (s.type==='path') { if (s.points.length) { r.push({x:s.points[0][0],y:s.points[0][1]}); if (s.points.length>1) r.push({x:s.points.at(-1)[0],y:s.points.at(-1)[1]}); } }
    else r.push({x:s.start_x,y:s.start_y},{x:s.end_x,y:s.end_y});
  }
  return r;
}
function findSnap(pos) { return allEndpoints().find(e=>Math.hypot(pos.x-e.x,pos.y-e.y)<CLOSE_THR*2)||null; }

// ── Hit test ──────────────────────────────────────────────────────────────────
function nearSeg(p,x1,y1,x2,y2,tol) {
  const dx=x2-x1,dy=y2-y1;
  if (!dx&&!dy) return Math.hypot(p.x-x1,p.y-y1)<tol;
  const t=Math.max(0,Math.min(1,((p.x-x1)*dx+(p.y-y1)*dy)/(dx*dx+dy*dy)));
  return Math.hypot(p.x-(x1+t*dx),p.y-(y1+t*dy))<tol;
}
function inShape(p,s) {
  if (s.type==='path') {
    const tol=s.stroke_width+5,pts=s.points,n=pts.length;
    for (let i=0;i<n-1;i++) if (nearSeg(p,pts[i][0],pts[i][1],pts[i+1][0],pts[i+1][1],tol)) return true;
    if (s.closed&&n>=3&&nearSeg(p,pts[n-1][0],pts[n-1][1],pts[0][0],pts[0][1],tol)) return true;
    return false;
  }
  if (s.type==='text') { const t=4; return p.x>=s.start_x-t&&p.x<=s.end_x+t&&p.y>=s.start_y-t&&p.y<=s.end_y+t; }
  const t=s.stroke_width+5;
  return p.x>=Math.min(s.start_x,s.end_x)-t&&p.x<=Math.max(s.start_x,s.end_x)+t
      && p.y>=Math.min(s.start_y,s.end_y)-t&&p.y<=Math.max(s.start_y,s.end_y)+t;
}
function hitTest(p) { for (let i=S.shapes.length-1;i>=0;i--) if (inShape(p,S.shapes[i])) return S.shapes[i]; return null; }

// ── Path/text handle helpers ──────────────────────────────────────────────────
function pathHandleAt(pos,s) {
  const pts=s.points,n=pts.length; if (n<2) return null;
  const segs=s.closed?n:n-1;
  for (let i=0;i<segs;i++) {
    const ei=(s.closed&&i===n-1)?0:i+1;
    const [x1,y1]=pts[i],[x2,y2]=pts[ei];
    const mx=(x1+x2)/2,my=(y1+y2)/2,c=i<s.curves.length?s.curves[i]:0;
    const dx=x2-x1,dy=y2-y1,len=Math.hypot(dx,dy);
    let hx=mx,hy=my;
    if (len>0){const nx=-dy/len,ny=dx/len;hx=mx+nx*c;hy=my+ny*c;}
    if (Math.hypot(pos.x-hx,pos.y-hy)<12) return i;
  }
  return null;
}
function textResizeHandle(pos,s) { return Math.hypot(pos.x-s.end_x,pos.y-s.end_y)<8; }

// ── Text metrics ──────────────────────────────────────────────────────────────
function measureTxt(text,fam,sz) {
  cx.save(); cx.font=`${sz}pt ${fam}`;
  const m=cx.measureText(text);
  const asc=m.actualBoundingBoxAscent??sz*0.8, desc=m.actualBoundingBoxDescent??sz*0.2;
  cx.restore(); return {w:m.width,h:asc+desc,asc};
}
function recomputeText(s) { const m=measureTxt(s.text,s.font_family,s.font_size); s.end_x=s.start_x+m.w; s.end_y=s.start_y+m.h; }

// ── Shape factory ─────────────────────────────────────────────────────────────
function mkShape(type,sx,sy,ex,ey,o={}) {
  return { type, start_x:sx, start_y:sy, end_x:ex, end_y:ey,
    rotation:o.rotation??0, stroke_width:o.stroke_width??S.strokeWidth,
    stroke_color:o.stroke_color??S.strokeColor, corner_radius:o.corner_radius??S.defaultCornerRadius,
    points:o.points??[], curves:o.curves??[], closed:o.closed??false,
    text:o.text??'', font_family:o.font_family??S.textFontFamily, font_size:o.font_size??S.textFontSize,
    id:o.id??Math.random().toString(36).slice(2) };
}

// ── Mouse events ──────────────────────────────────────────────────────────────
cv.addEventListener('mousedown', onDown);
cv.addEventListener('mousemove', onMove);
cv.addEventListener('mouseup',   onUp);
cv.addEventListener('dblclick',  onDbl);
cv.addEventListener('contextmenu', e=>{ e.preventDefault(); });
cv.addEventListener('wheel', onWheel, {passive:false});
cv.addEventListener('mouseleave', ()=>{ S.hover=null; redraw(); });

// ── Touch → draw (mobile) ─────────────────────────────────────────────────────
function touchEvt(e) {
  const t = e.touches.length ? e.touches[0] : e.changedTouches[0];
  return { clientX:t.clientX, clientY:t.clientY, button:0, shiftKey:false, preventDefault:()=>{} };
}
let _lastTap = 0;
cv.addEventListener('touchstart', e => {
  e.preventDefault();
  const fake = touchEvt(e);
  const now = Date.now();
  if (now - _lastTap < 300) onDbl(fake);
  _lastTap = now;
  onDown(fake);
}, { passive:false });
cv.addEventListener('touchmove',   e => { e.preventDefault(); onMove(touchEvt(e)); }, { passive:false });
cv.addEventListener('touchend',    e => { e.preventDefault(); onUp(touchEvt(e));   }, { passive:false });
cv.addEventListener('touchcancel', e => { e.preventDefault(); onUp(touchEvt(e));   }, { passive:false });

function onDown(e) {
  e.preventDefault();
  const pos = canvasPos(e);

  if (e.button===2) {
    if (S.mode==='select') {
      S.rotating=hitTest(pos);
      if (S.rotating) { saveState(); S.rotAngle=calcAngle(pos); }
    } else if (S.tool==='path'&&S.pathPoints.length) {
      const ep=findSnap(pos), fin=ep?ep:(S.gridSnapEnabled?snapGrid(pos):pos);
      S.pathPoints.push([fin.x,fin.y]);
      if (S.pathPoints.length>=2) finalizePath(false); else { S.pathPoints=[]; redraw(); }
    }
    return;
  }
  if (e.button!==0) return;

  if (S.mode==='select') {
    for (const s of S.selected) if (s.type==='text'&&textResizeHandle(pos,s)) {
      saveState(); S.textResize=s; S.textResizeStart=pos; S.textResizeStartSz=s.font_size;
      S.textResizeH=Math.max(1,s.end_y-s.start_y); return;
    }
    for (const s of S.selected) if (s.type==='path') {
      const hi=pathHandleAt(pos,s);
      if (hi!==null) { saveState(); S.curveDrag={s,i:hi}; return; }
    }
    const hit=hitTest(pos);
    if (hit) {
      if (e.shiftKey) { const idx=S.selected.indexOf(hit); idx>=0?S.selected.splice(idx,1):S.selected.push(hit); }
      else if (!S.selected.includes(hit)) S.selected=[hit];
      if (S.selected.length) {
        saveState();
        S.moving=[...S.selected]; S.moveStart=pos; S.moveStartSnap=snapGrid(pos);
        S.moveOrigins=S.moving.map(s=>({sx:s.start_x,sy:s.start_y,ex:s.end_x,ey:s.end_y,pts:JSON.parse(JSON.stringify(s.points))}));
        onSel(S.selected.at(-1));
      }
    } else {
      if (!e.shiftKey) { S.selected=[]; selWidget(); }
    }
    redraw();
  } else {
    if (S.tool==='path') {
      const ep=findSnap(pos), sn=ep?ep:(S.gridSnapEnabled?snapGrid(pos):pos);
      if (S.pathPoints.length>=3) {
        const [x0,y0]=S.pathPoints[0];
        if (Math.hypot(sn.x-x0,sn.y-y0)<CLOSE_THR) { finalizePath(true); return; }
      }
      S.pathPoints.push([sn.x,sn.y]); redraw();
    } else if (S.tool==='text') {
      const sn=S.gridSnapEnabled?snapGrid(pos):pos;
      const txt=prompt('Enter text:'); if (!txt||!txt.trim()) return;
      saveState();
      const m=measureTxt(txt,S.textFontFamily,S.textFontSize);
      S.shapes.push(mkShape('text',sn.x,sn.y,sn.x+m.w,sn.y+m.h,{text:txt.trim()})); redraw();
    } else {
      let st=findSnap(pos)||(S.gridSnapEnabled?snapGrid(pos):pos);
      S.startPos=st; S.curPos=st; S.isDrawing=true;
    }
  }
}

function onMove(e) {
  const pos=canvasPos(e); S.cursor=pos; S.curPos=pos;

  if (S.mode==='select'&&!S.moving.length&&!S.rotating&&!S.curveDrag&&!S.textResize) {
    const prev=S.hover; S.hover=hitTest(pos); if (S.hover!==prev) redraw();
  }

  if (S.textResize) {
    const dy=pos.y-S.textResizeStart.y;
    const ns=Math.max(6,Math.round(S.textResizeStartSz*(1+dy/S.textResizeH)));
    if (ns!==S.textResize.font_size) { S.textResize.font_size=ns; recomputeText(S.textResize); } redraw();
  } else if (S.curveDrag) {
    const {s,i}=S.curveDrag, pts=s.points, n=pts.length;
    const ei=(s.closed&&i===n-1)?0:i+1;
    const [x1,y1]=pts[i],[x2,y2]=pts[ei],mx=(x1+x2)/2,my=(y1+y2)/2;
    const dx=x2-x1,dy2=y2-y1,len=Math.hypot(dx,dy2);
    if (len>0) { const nx=-dy2/len,ny=dx/len; while(s.curves.length<=i)s.curves.push(0); s.curves[i]=(pos.x-mx)*nx+(pos.y-my)*ny; }
    redraw();
  } else if (S.moving.length) {
    let dx,dy;
    if (S.gridSnapEnabled) { const sp=snapGrid(pos); dx=sp.x-S.moveStartSnap.x; dy=sp.y-S.moveStartSnap.y; }
    else { dx=pos.x-S.moveStart.x; dy=pos.y-S.moveStart.y; }
    S.moving.forEach((s,i)=>{ const o=S.moveOrigins[i]; s.start_x=o.sx+dx; s.start_y=o.sy+dy; s.end_x=o.ex+dx; s.end_y=o.ey+dy; s.points=o.pts.map(p=>[p[0]+dx,p[1]+dy]); });
    redraw();
  } else if (S.tool==='path'&&S.mode==='draw') {
    const ep=findSnap(pos); S.snapEp=ep; S.curPos=ep?ep:(S.gridSnapEnabled?snapGrid(pos):pos); redraw();
  } else if (S.isDrawing) {
    let p=pos;
    if (S.snapEnabled&&e.shiftKey) p=snapAngle(pos);
    else if (S.gridSnapEnabled) p=snapGrid(pos);
    const ep=findSnap(pos);
    S.curPos=ep?ep:p; S.snapEp=ep||null; redraw();
  } else if (S.rotating) {
    const a=calcAngle(pos), delta=a-S.rotAngle; S.rotAngle=a;
    let nr=S.rotating.rotation+delta;
    S.rotating.rotation=(S.snapEnabled&&e.shiftKey)?snapRot(nr):nr; redraw();
  } else if (S.gridSnapEnabled&&S.mode==='draw') redraw();
}

function onUp(e) {
  if (e.button===2) { S.rotating=null; return; }
  if (e.button!==0) return;
  if (S.textResize) { onSel(S.textResize); S.textResize=null; return; }
  if (S.curveDrag) { S.curveDrag=null; return; }
  if (S.moving.length) { S.moving=[]; S.moveOrigins=[]; return; }
  if (S.isDrawing) {
    S.isDrawing=false; saveState();
    S.shapes.push(mkShape(S.tool,S.startPos.x,S.startPos.y,S.curPos.x,S.curPos.y));
    S.snapEp=null; redraw();
  }
}

function onDbl(e) {
  const pos=canvasPos(e);
  if (S.mode==='select') {
    const hit=hitTest(pos);
    if (hit&&hit.type==='text') {
      const t=prompt('Edit text:',hit.text); if (t===null) return;
      saveState(); hit.text=t.trim()||hit.text; recomputeText(hit); onSel(hit); redraw(); return;
    }
  }
  if (S.mode==='draw'&&S.tool==='path'&&S.pathPoints.length>=2) finalizePath(false);
}

function onWheel(e) {
  e.preventDefault();
  if (e.ctrlKey) {
    S.zoom = Math.min(8, Math.max(0.1, S.zoom * (e.deltaY < 0 ? 1.1 : 1/1.1)));
    cv.style.width  = Math.round(S.canvasW * S.zoom) + 'px';
    cv.style.height = Math.round(S.canvasH * S.zoom) + 'px';
    return;
  }
  const delta=e.deltaY<0?1:-1;
  const targets=S.rotating?[S.rotating]:(S.mode==='select'?S.selected:[]);
  if (targets.length) {
    for (const t of targets) t.rotation=(S.snapEnabled&&e.shiftKey)?snapRot(t.rotation)+Math.sign(delta)*22.5:t.rotation+delta;
    redraw();
  }
}

function calcAngle(p) { return Math.atan2(p.y-S.canvasH/2,p.x-S.canvasW/2)*180/Math.PI; }

function finalizePath(closed) {
  if (S.pathPoints.length<2) { S.pathPoints=[]; redraw(); return; }
  saveState();
  const pts=[...S.pathPoints];
  S.shapes.push(mkShape('path',pts[0][0],pts[0][1],pts.at(-1)[0],pts.at(-1)[1],{points:pts,curves:[],closed}));
  S.pathPoints=[]; S.snapEp=null; redraw();
}

// ── Keyboard ──────────────────────────────────────────────────────────────────
document.addEventListener('keydown', e=>{
  if (['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName)) return;
  const ctrl=e.ctrlKey||e.metaKey;
  if (ctrl) {
    if (e.key==='z'){e.preventDefault();e.shiftKey?redo():undo();return;}
    if (e.key==='y'){e.preventDefault();redo();return;}
    if (e.key==='s'){e.preventDefault();saveProject();return;}
    if (e.key==='o'){e.preventDefault();document.getElementById('file-in').click();return;}
  }
  if (e.key==='Escape'){S.pathPoints=[];redraw();}
  if (e.key==='Delete'||e.key==='Backspace') {
    if (S.pathPoints.length){S.pathPoints.pop();redraw();return;}
    const del=S.selected.filter(s=>S.shapes.includes(s));
    if (del.length){saveState();del.forEach(s=>S.shapes.splice(S.shapes.indexOf(s),1));S.selected=[];selWidget();redraw();}
  }
  const map={q:'select',l:'line',c:'circle',s:'square',t:'triangle',p:'path',w:'text'};
  if (!ctrl&&map[e.key.toLowerCase()]) {
    const v=map[e.key.toLowerCase()]; v==='select'?setMode('select'):setTool(v);
  }
});

// ── Drawing ───────────────────────────────────────────────────────────────────
function redraw() {
  cx.clearRect(0,0,cv.width,cv.height);
  if (S.showBackground){cx.fillStyle=S.bgColor;cx.fillRect(0,0,S.canvasW,S.canvasH);}
  else drawChecker();
  if (S.gridEnabled) drawGrid();
  for (const s of S.shapes) {
    const sel=S.selected.includes(s), hov=s===S.hover&&!sel;
    drawShape(cx,s,{sel,hov});
    if (sel&&s.type==='path') drawCurveHandles(cx,s);
  }
  if (S.isDrawing) drawShape(cx,mkShape(S.tool,S.startPos.x,S.startPos.y,S.curPos.x,S.curPos.y,{stroke_width:S.strokeWidth,stroke_color:S.strokeColor}),{preview:true});
  if (S.pathPoints.length&&S.mode==='draw') drawPathPreview();
  if (S.gridSnapEnabled&&S.mode==='draw'&&S.tool!=='path'&&S.tool!=='text') {
    const sn=snapGrid(S.cursor);
    cx.save(); cx.strokeStyle='#0099ff'; cx.fillStyle='rgba(0,153,255,.62)'; cx.lineWidth=1;
    cx.beginPath(); cx.arc(sn.x,sn.y,4,0,Math.PI*2); cx.fill(); cx.stroke();
    if (S.isDrawing){cx.fillStyle='rgba(0,200,100,.78)';cx.beginPath();cx.arc(S.startPos.x,S.startPos.y,4,0,Math.PI*2);cx.fill();}
    cx.restore();
  }
  if (S.snapEp&&S.mode==='draw') {
    cx.save(); cx.strokeStyle='#ff9900'; cx.lineWidth=2;
    cx.beginPath(); cx.arc(S.snapEp.x,S.snapEp.y,8,0,Math.PI*2); cx.stroke(); cx.restore();
  }
}

function drawChecker() {
  const sz=16;
  for (let r=0;r<S.canvasH;r+=sz) for (let c2=0;c2<S.canvasW;c2+=sz) {
    cx.fillStyle=((r/sz+c2/sz)%2===0)?'#ccc':'#fff'; cx.fillRect(c2,r,sz,sz);
  }
}

function drawGrid() {
  const bg=S.bgColor, r=parseInt(bg.slice(1,3),16), g=parseInt(bg.slice(3,5),16), b=parseInt(bg.slice(5,7),16);
  cx.strokeStyle=(0.299*r+0.587*g+0.114*b>128)?'rgba(0,0,0,.12)':'rgba(255,255,255,.12)';
  cx.lineWidth=0.5; cx.beginPath();
  for (let x=0;x<=S.canvasW;x+=GRID){cx.moveTo(x,0);cx.lineTo(x,S.canvasH);}
  if (S.canvasW%GRID!==0){cx.moveTo(S.canvasW,0);cx.lineTo(S.canvasW,S.canvasH);}
  for (let y=0;y<=S.canvasH;y+=GRID){cx.moveTo(0,y);cx.lineTo(S.canvasW,y);}
  if (S.canvasH%GRID!==0){cx.moveTo(0,S.canvasH);cx.lineTo(S.canvasW,S.canvasH);}
  cx.stroke();
}

function drawShape(c,s,{preview=false,sel=false,hov=false}={}) {
  c.save(); c.lineCap='round'; c.lineJoin='round';
  let col=s.stroke_color, lw=Math.max(1,s.stroke_width);
  if (hov){col='#88bbff';lw+=1;} if (sel) col='#ff6b6b'; if (preview) col=S.strokeColor;
  c.strokeStyle=col; c.lineWidth=lw;
  if (s.type==='path'){drawPath(c,s);c.restore();return;}
  const scx=(s.start_x+s.end_x)/2, scy=(s.start_y+s.end_y)/2;
  c.translate(scx,scy); c.rotate(s.rotation*Math.PI/180); c.translate(-scx,-scy);
  if (s.type==='text') { drawTextShape(c,s,col,sel,hov); }
  else if (s.type==='line') { c.beginPath();c.moveTo(s.start_x,s.start_y);c.lineTo(s.end_x,s.end_y);c.stroke(); }
  else if (s.type==='circle') { const r=Math.hypot(s.end_x-s.start_x,s.end_y-s.start_y)/2; c.beginPath();c.arc(scx,scy,r,0,Math.PI*2);c.stroke(); }
  else if (s.type==='square') {
    const x=Math.min(s.start_x,s.end_x),y=Math.min(s.start_y,s.end_y),w=Math.abs(s.end_x-s.start_x),h=Math.abs(s.end_y-s.start_y);
    c.beginPath();
    if (s.corner_radius>0) { const r=s.corner_radius; c.moveTo(x+r,y);c.lineTo(x+w-r,y);c.arcTo(x+w,y,x+w,y+r,r);c.lineTo(x+w,y+h-r);c.arcTo(x+w,y+h,x+w-r,y+h,r);c.lineTo(x+r,y+h);c.arcTo(x,y+h,x,y+h-r,r);c.lineTo(x,y+r);c.arcTo(x,y,x+r,y,r);c.closePath(); }
    else c.rect(x,y,w,h);
    c.stroke();
  } else if (s.type==='triangle') {
    const x1=s.start_x,y1=s.start_y,x2=s.end_x,y2=s.end_y,mx=(x1+x2)/2,my=(y1+y2)/2,dx=x2-x1,dy=y2-y1;
    c.beginPath();c.moveTo(x1,y1);c.lineTo(x2,y2);c.lineTo(mx-dy/2,my+dx/2);c.closePath();c.stroke();
  }
  c.restore();
}

function drawPath(c,s) {
  const pts=s.points,n=pts.length; if (n<2) return;
  c.beginPath(); c.moveTo(pts[0][0],pts[0][1]);
  const segs=s.closed?n:n-1;
  for (let i=0;i<segs;i++) {
    const ei=(s.closed&&i===n-1)?0:i+1;
    const [x1,y1]=pts[i],[x2,y2]=pts[ei],cv2=i<s.curves.length?s.curves[i]:0;
    if (cv2) { const mx=(x1+x2)/2,my=(y1+y2)/2,dx=x2-x1,dy=y2-y1,len=Math.hypot(dx,dy); if(len>0){const nx=-dy/len,ny=dx/len;c.quadraticCurveTo(mx+nx*cv2,my+ny*cv2,x2,y2);}else c.lineTo(x2,y2); }
    else c.lineTo(x2,y2);
  }
  if (s.closed) c.closePath(); c.stroke();
}

function drawTextShape(c,s,col,sel,hov) {
  c.font=`${s.font_size}pt ${s.font_family}`;
  const m=c.measureText(s.text), asc=m.actualBoundingBoxAscent??s.font_size*0.8;
  if (sel||hov) {
    const w=s.end_x-s.start_x,h=s.end_y-s.start_y;
    c.save();c.strokeStyle=sel?'#ff6b6b':'#88bbff';c.lineWidth=1;c.setLineDash([4,3]);
    c.strokeRect(s.start_x-2,s.start_y-2,w+4,h+4);c.restore();
    if (sel) { c.save();c.strokeStyle='#ff6b6b';c.fillStyle='#fff';c.lineWidth=1;c.fillRect(s.end_x-5,s.end_y-5,10,10);c.strokeRect(s.end_x-5,s.end_y-5,10,10);c.restore(); }
  }
  c.fillStyle=col; c.fillText(s.text,s.start_x,s.start_y+asc);
}

function drawPathPreview() {
  const pts=S.pathPoints;
  cx.save();cx.lineCap='round';cx.lineJoin='round';cx.strokeStyle=S.strokeColor;cx.lineWidth=Math.max(1,S.strokeWidth);
  cx.beginPath();cx.moveTo(pts[0][0],pts[0][1]);
  for (let i=1;i<pts.length;i++) cx.lineTo(pts[i][0],pts[i][1]);
  cx.lineTo(S.curPos.x,S.curPos.y);cx.stroke();
  if (pts.length>=3) { cx.strokeStyle='#00cc44';cx.fillStyle='rgba(0,204,68,.39)';cx.lineWidth=2;cx.beginPath();cx.arc(pts[0][0],pts[0][1],CLOSE_THR,0,Math.PI*2);cx.fill();cx.stroke(); }
  cx.fillStyle='rgba(0,153,255,.78)';cx.strokeStyle='#0099ff';cx.lineWidth=1;
  for (const p of pts){cx.beginPath();cx.arc(p[0],p[1],4,0,Math.PI*2);cx.fill();cx.stroke();}
  cx.restore();
}

function drawCurveHandles(c,s) {
  const pts=s.points,n=pts.length; if (n<2) return;
  const segs=s.closed?n:n-1; c.save();
  for (let i=0;i<segs;i++) {
    const ei=(s.closed&&i===n-1)?0:i+1;
    const [x1,y1]=pts[i],[x2,y2]=pts[ei],mx=(x1+x2)/2,my=(y1+y2)/2,cv2=i<s.curves.length?s.curves[i]:0;
    const dx=x2-x1,dy=y2-y1,len=Math.hypot(dx,dy);
    let hx=mx,hy=my;
    if(len>0){const nx=-dy/len,ny=dx/len;hx=mx+nx*cv2;hy=my+ny*cv2;}
    c.strokeStyle='rgba(255,153,0,.47)';c.lineWidth=1;c.beginPath();c.moveTo(mx,my);c.lineTo(hx,hy);c.stroke();
    const r=5;c.fillStyle='#ff9900';c.beginPath();c.moveTo(hx,hy-r);c.lineTo(hx+r,hy);c.lineTo(hx,hy+r);c.lineTo(hx-r,hy);c.closePath();c.fill();
  }
  c.restore();
}

// ── Tool controls ─────────────────────────────────────────────────────────────
function setMode(mode) {
  S.mode=mode; S.isDrawing=false; S.pathPoints=[]; S.moving=[]; S.rotating=null; S.curveDrag=null;
  cv.style.cursor=mode==='select'?'default':'crosshair'; updateToolBtns(); redraw();
}
function setTool(tool) { S.tool=tool; setMode('draw'); }
function updateToolBtns() {
  ['select','line','circle','square','triangle','path','text'].forEach(t=>{
    const el=document.getElementById('tb-'+t);
    el.classList.toggle('active',(S.mode==='select'&&t==='select')||(S.mode==='draw'&&t===S.tool));
  });
}
function toggleGrid(btn) { S.gridEnabled=!S.gridEnabled; btn.classList.toggle('toggled',S.gridEnabled); redraw(); }

// ── Palette & color ───────────────────────────────────────────────────────────
const palSel=document.getElementById('pal-sel');
PALETTES.forEach((p,i)=>{ const o=document.createElement('option');o.value=i;o.textContent=p.name;palSel.appendChild(o); });

function applyPalette(idx) {
  const p=PALETTES[idx], old=S.palette; S.palette=p; S.bgColor=p.bg;
  for (const s of S.shapes) {
    if (s.stroke_color.toLowerCase()===old.icon.toLowerCase()) s.stroke_color=p.icon;
    else if (s.stroke_color.toLowerCase()===old.acc.toLowerCase()) s.stroke_color=p.acc;
  }
  setColor(p.icon); refreshSwatches(); redraw();
}
function refreshSwatches() {
  const p=S.palette;
  const sbg=document.getElementById('sw-bg'),si=document.getElementById('sw-icon'),sa=document.getElementById('sw-acc');
  sbg.style.background=p.bg; sbg.onclick=()=>setColor(p.bg);
  si.style.background=p.icon; si.onclick=()=>setColor(p.icon);
  sa.style.background=p.acc; sa.onclick=()=>setColor(p.acc);
}
function setColor(hex) { S.strokeColor=hex; document.getElementById('active-swatch').style.background=hex; }

let colorCb=null;
function pickCustom() { colorCb=c=>setColor(c); const el=document.getElementById('color-in'); el.value=S.strokeColor; el.click(); }
function pickSelColor() {
  if (!S.selected.length) return;
  colorCb=c=>{ saveState(); for(const s of S.selected) s.stroke_color=c; selWidget(); redraw(); };
  const el=document.getElementById('color-in'); el.value=S.selected.at(-1).stroke_color; el.click();
}
function onColorPick(v) { if (colorCb){colorCb(v);colorCb=null;} }

// ── Fonts ─────────────────────────────────────────────────────────────────────
const fontSel=document.getElementById('font-sel');
FONTS.forEach(f=>{ const o=document.createElement('option');o.value=f;o.textContent=f;if(f===S.textFontFamily)o.selected=true;fontSel.appendChild(o); });
function updateSelFont() { for(const s of S.selected) if(s.type==='text'){s.font_family=S.textFontFamily;s.font_size=S.textFontSize;recomputeText(s);} redraw(); }

// ── Sidebar ───────────────────────────────────────────────────────────────────
function setCornerRadius(v) { S.defaultCornerRadius=v; for(const s of S.selected) s.corner_radius=v; redraw(); }
function makeSquare() { document.getElementById('ch').value=document.getElementById('cw').value; }
function applySize() { S.canvasW=+document.getElementById('cw').value; S.canvasH=+document.getElementById('ch').value; cv.width=S.canvasW; cv.height=S.canvasH; redraw(); }
function confirmClear() { if(confirm('Delete all shapes? Cannot be undone.')) { saveState();S.shapes=[];S.selected=[];S.pathPoints=[];selWidget();redraw(); } }

function onSel(s) {
  document.getElementById('cr').value=Math.round(s.corner_radius);
  selWidget(s);
  const lines=[`Type: ${s.type}`,`Rotation: ${s.rotation.toFixed(1)}`,`Stroke: ${s.stroke_width}`,`Color: ${s.stroke_color}`];
  if (s.type==='text') lines.push(`Text: ${s.text}`,`Font: ${s.font_family} ${s.font_size}pt`);
  document.getElementById('info').textContent=lines.join('\n');
}
function selWidget(s) {
  const row=document.getElementById('sel-row'), btn=document.getElementById('sel-color');
  const active=s||S.selected.at(-1);
  if (active&&S.selected.length) { row.style.opacity='1';row.style.pointerEvents='auto';btn.style.background=active.stroke_color; }
  else { row.style.opacity='.4';row.style.pointerEvents='none'; document.getElementById('info').textContent='Ready'; }
}

// ── Save / Load ───────────────────────────────────────────────────────────────
function saveProject() {
  const data={ shapes:S.shapes.map(s=>({...s})), palette:S.palette.name, show_background:S.showBackground, canvas_w:S.canvasW, canvas_h:S.canvasH };
  const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  a.download='project.iconproj'; a.click();
  S.dirty = false;
}
function onFileLoad(inp) {
  const f=inp.files[0]; if(!f) return;
  const r=new FileReader();
  r.onload=e=>{ try {
    const d=JSON.parse(e.target.result);
    S.shapes=(d.shapes||[]).map(s=>mkShape(s.type,s.start_x,s.start_y,s.end_x,s.end_y,s));
    const pal=PALETTES.find(p=>p.name===d.palette)||PALETTES[0];
    palSel.value=PALETTES.indexOf(pal); S.palette=pal; S.bgColor=pal.bg; setColor(pal.icon); refreshSwatches();
    S.showBackground=d.show_background!==false; document.getElementById('chk-bg').checked=S.showBackground;
    if (d.canvas_w) { S.canvasW=d.canvas_w;S.canvasH=d.canvas_h;cv.width=S.canvasW;cv.height=S.canvasH; document.getElementById('cw').value=S.canvasW; document.getElementById('ch').value=S.canvasH; }
    S.selected=[]; S.dirty=false; selWidget(); redraw();
  } catch(err){alert('Load failed: '+err.message);} };
  r.readAsText(f); inp.value='';
}

// ── Export SVG ────────────────────────────────────────────────────────────────
function exportSVG() {
  const w=S.canvasW,h=S.canvasH;
  const lines=[`<?xml version="1.0" encoding="UTF-8"?>`,`<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">`];
  if (S.showBackground) lines.push(`<rect width="${w}" height="${h}" fill="${S.palette.bg}"/>`);
  for (const s of S.shapes) lines.push(toSVG(s));
  lines.push('</svg>');
  const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([lines.join('\n')],{type:'image/svg+xml'}));
  a.download='icon.svg'; a.click();
}
function toSVG(s) {
  const sw=Math.max(1,Math.round(s.stroke_width)),c=s.stroke_color;
  if (s.type==='path') {
    const pts=s.points,n=pts.length; if(n<2) return '';
    let d=`M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
    const segs=s.closed?n:n-1;
    for(let i=0;i<segs;i++){const ei=(s.closed&&i===n-1)?0:i+1;const[x1,y1]=pts[i],[x2,y2]=pts[ei],cv2=i<s.curves.length?s.curves[i]:0;if(cv2){const mx=(x1+x2)/2,my=(y1+y2)/2,dx=x2-x1,dy=y2-y1,len=Math.hypot(dx,dy);if(len>0){const nx=-dy/len,ny=dx/len;d+=` Q ${(mx+nx*cv2).toFixed(1)} ${(my+ny*cv2).toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`;}else d+=` L ${x2.toFixed(1)} ${y2.toFixed(1)}`;}else d+=` L ${x2.toFixed(1)} ${y2.toFixed(1)}`;}
    if(s.closed)d+=' Z';
    return `<path d="${d}" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round"/>`;
  }
  if (s.type==='text') {
    const scx=(s.start_x+s.end_x)/2,scy=(s.start_y+s.end_y)/2;
    const tr=`transform="translate(${scx.toFixed(1)},${scy.toFixed(1)}) rotate(${s.rotation.toFixed(2)}) translate(${(-scx).toFixed(1)},${(-scy).toFixed(1)})"`;
    const m=measureTxt(s.text,s.font_family,s.font_size);
    const safe=s.text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    return `<text x="${Math.round(s.start_x)}" y="${Math.round(s.start_y+m.asc)}" font-family="${s.font_family}" font-size="${s.font_size}pt" fill="${c}" ${tr}>${safe}</text>`;
  }
  const scx=(s.start_x+s.end_x)/2,scy=(s.start_y+s.end_y)/2;
  const tr=`transform="translate(${scx} ${scy}) rotate(${s.rotation}) translate(${-scx} ${-scy})"`;
  if (s.type==='line') return `<line x1="${Math.round(s.start_x)}" y1="${Math.round(s.start_y)}" x2="${Math.round(s.end_x)}" y2="${Math.round(s.end_y)}" stroke="${c}" stroke-width="${sw}" stroke-linecap="round" ${tr}/>`;
  if (s.type==='circle') { const r=Math.hypot(s.end_x-s.start_x,s.end_y-s.start_y)/2; return `<circle cx="${Math.round(scx)}" cy="${Math.round(scy)}" r="${r.toFixed(2)}" fill="none" stroke="${c}" stroke-width="${sw}" ${tr}/>`; }
  if (s.type==='square') { const x=Math.min(s.start_x,s.end_x),y=Math.min(s.start_y,s.end_y),rw=Math.abs(s.end_x-s.start_x),rh=Math.abs(s.end_y-s.start_y),cr=s.corner_radius; const rx=cr>0?` rx="${cr.toFixed(1)}" ry="${cr.toFixed(1)}"`:'' ; return `<rect x="${Math.round(x)}" y="${Math.round(y)}" width="${Math.round(rw)}" height="${Math.round(rh)}"${rx} fill="none" stroke="${c}" stroke-width="${sw}" ${tr}/>`; }
  if (s.type==='triangle') { const x1=s.start_x,y1=s.start_y,x2=s.end_x,y2=s.end_y,mx=(x1+x2)/2,my=(y1+y2)/2,dx=x2-x1,dy=y2-y1; return `<polygon points="${Math.round(x1)},${Math.round(y1)} ${Math.round(x2)},${Math.round(y2)} ${Math.round(mx-dy/2)},${Math.round(my+dx/2)}" fill="none" stroke="${c}" stroke-width="${sw}" ${tr}/>`; }
  return '';
}

// ── Offscreen render ──────────────────────────────────────────────────────────
function renderOffscreen(sz) {
  const oc=document.createElement('canvas'); oc.width=S.canvasW; oc.height=S.canvasH;
  const oc2=oc.getContext('2d'); oc2.lineCap='round'; oc2.lineJoin='round';
  if (S.showBackground){oc2.fillStyle=S.bgColor;oc2.fillRect(0,0,S.canvasW,S.canvasH);}
  for (const s of S.shapes) {
    oc2.save(); oc2.lineCap='round'; oc2.lineJoin='round'; oc2.strokeStyle=s.stroke_color; oc2.lineWidth=Math.max(1,s.stroke_width);
    if (s.type==='path'){drawPath(oc2,s);oc2.restore();continue;}
    const scx=(s.start_x+s.end_x)/2,scy=(s.start_y+s.end_y)/2;
    oc2.translate(scx,scy);oc2.rotate(s.rotation*Math.PI/180);oc2.translate(-scx,-scy);
    if (s.type==='line'){oc2.beginPath();oc2.moveTo(s.start_x,s.start_y);oc2.lineTo(s.end_x,s.end_y);oc2.stroke();}
    else if (s.type==='circle'){const r=Math.hypot(s.end_x-s.start_x,s.end_y-s.start_y)/2;oc2.beginPath();oc2.arc(scx,scy,r,0,Math.PI*2);oc2.stroke();}
    else if (s.type==='square'){const x=Math.min(s.start_x,s.end_x),y=Math.min(s.start_y,s.end_y),w2=Math.abs(s.end_x-s.start_x),h2=Math.abs(s.end_y-s.start_y);oc2.beginPath();if(s.corner_radius>0){const r=s.corner_radius;oc2.moveTo(x+r,y);oc2.lineTo(x+w2-r,y);oc2.arcTo(x+w2,y,x+w2,y+r,r);oc2.lineTo(x+w2,y+h2-r);oc2.arcTo(x+w2,y+h2,x+w2-r,y+h2,r);oc2.lineTo(x+r,y+h2);oc2.arcTo(x,y+h2,x,y+h2-r,r);oc2.lineTo(x,y+r);oc2.arcTo(x,y,x+r,y,r);oc2.closePath();}else oc2.rect(x,y,w2,h2);oc2.stroke();}
    else if (s.type==='triangle'){const x1=s.start_x,y1=s.start_y,x2=s.end_x,y2=s.end_y,mx=(x1+x2)/2,my=(y1+y2)/2,dx=x2-x1,dy=y2-y1;oc2.beginPath();oc2.moveTo(x1,y1);oc2.lineTo(x2,y2);oc2.lineTo(mx-dy/2,my+dx/2);oc2.closePath();oc2.stroke();}
    else if (s.type==='text'){oc2.font=`${s.font_size}pt ${s.font_family}`;const mm=oc2.measureText(s.text);oc2.fillStyle=s.stroke_color;oc2.fillText(s.text,s.start_x,s.start_y+(mm.actualBoundingBoxAscent??s.font_size*0.8));}
    oc2.restore();
  }
  if (sz===S.canvasW) return oc;
  const sc=document.createElement('canvas');sc.width=sz;sc.height=sz;
  sc.getContext('2d').drawImage(oc,0,0,sz,sz); return sc;
}

// ── iOS export ────────────────────────────────────────────────────────────────
async function exportIOS() {
  if (typeof JSZip==='undefined'){alert('JSZip not loaded.');return;}
  const specs=[[20,1,'iphone'],[20,2,'iphone'],[20,3,'iphone'],[29,1,'iphone'],[29,2,'iphone'],[29,3,'iphone'],[40,1,'iphone'],[40,2,'iphone'],[40,3,'iphone'],[60,2,'iphone'],[60,3,'iphone'],[20,1,'ipad'],[20,2,'ipad'],[29,1,'ipad'],[29,2,'ipad'],[40,1,'ipad'],[40,2,'ipad'],[76,1,'ipad'],[76,2,'ipad'],[1024,1,'ios-marketing']];
  const zip=new JSZip(),folder=zip.folder('AppIcon.appiconset'),seen=new Map(),images=[];
  for (const [lg,sc,id] of specs) {
    const px=lg*sc,fn=`icon-${lg}@${sc}x-${id}.png`;
    if (!seen.has(px)) seen.set(px,await new Promise(r=>renderOffscreen(px).toBlob(r,'image/png')));
    folder.file(fn,seen.get(px)); images.push({filename:fn,idiom:id,scale:`${sc}x`,size:`${lg}x${lg}`});
  }
  folder.file('Contents.json',JSON.stringify({images,info:{author:'xcode',version:1}},null,2));
  const a=document.createElement('a');a.href=URL.createObjectURL(await zip.generateAsync({type:'blob'}));a.download='AppIcon.appiconset.zip';a.click();
}

// ── Android export ────────────────────────────────────────────────────────────
async function exportAndroid() {
  if (typeof JSZip==='undefined'){alert('JSZip not loaded.');return;}
  const densities=[['mipmap-mdpi',48],['mipmap-hdpi',72],['mipmap-xhdpi',96],['mipmap-xxhdpi',144],['mipmap-xxxhdpi',192]];
  const zip=new JSZip(),res=zip.folder('res');
  for (const [d,sz] of densities) res.folder(d).file('ic_launcher.png',await new Promise(r=>renderOffscreen(sz).toBlob(r,'image/png')));
  const a=document.createElement('a');a.href=URL.createObjectURL(await zip.generateAsync({type:'blob'}));a.download='android-res.zip';a.click();
}

// ── Sidebar toggle (mobile) ───────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('active');
}

// ── Mobile tab switching ──────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tb-group').forEach(g => g.classList.remove('tb-active'));
  document.querySelectorAll('#tb-tabs .tab-btn[data-tab]').forEach(b => b.classList.remove('active'));
  const group = document.getElementById('tbg-' + name);
  if (group) group.classList.add('tb-active');
  const btn = document.querySelector('#tb-tabs [data-tab="' + name + '"]');
  if (btn) btn.classList.add('active');
}

// ── Unsaved-changes guard ─────────────────────────────────────────────────────
window.addEventListener('beforeunload', e => {
  if (S.dirty) { e.preventDefault(); e.returnValue = ''; }
});

// ── Init ──────────────────────────────────────────────────────────────────────
refreshSwatches(); setColor(PALETTES[0].icon); initCanvas(); updateToolBtns(); switchTab('tools');
