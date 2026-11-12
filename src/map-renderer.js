// Cache dense route overlays at a bounded resolution; individual routes remain vector.
function createDenseOverlay() {
  let source=null, image=null, bounds=null;
  return function(ctx,routes,colors,view,w,h){
    if(routes.length<=200)return false;
    if(source!==routes){
      source=routes;let x0=Infinity,x1=-Infinity,y0=Infinity,y1=-Infinity;
      for(const r of routes)for(const p of r.parts)for(const [x,y] of p.coords){x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y)}
      bounds=[x0,y0,x1,y1];image=document.createElement('canvas');image.width=2048;image.height=2048;
      const g=image.getContext('2d');g.globalAlpha=.16;g.lineWidth=1;
      for(const r of routes){g.strokeStyle=colors[r.mode];for(const part of r.parts){g.setLineDash(r.mode==='transit'&&part.kind==='walking'?[5,4]:[]);g.beginPath();part.coords.forEach(([x,y],i)=>{const px=(x-x0)/(x1-x0)*2048,py=(y1-y)/(y1-y0)*2048;i?g.lineTo(px,py):g.moveTo(px,py)});g.stroke()}}
    }
    const [x0,y0,x1,y1]=bounds;
    // Return to vectors when zoomed past the raster's useful resolution.
    if((x1-x0)*.767*view.s>4096||(y1-y0)*view.s>4096)return false;
    ctx.drawImage(image,(x0-view.x)*.767*view.s+w/2,(view.y-y1)*view.s+h/2,(x1-x0)*.767*view.s,(y1-y0)*view.s);
    return true;
  };
}

// Cache vector paths once; clip off-screen geometry before canvas submission.
function createMapRenderer(ctx, canvas) {
  const cache=new WeakMap();
  const boundsFor=coords=>{
    let minX=Infinity,maxX=-Infinity,minY=Infinity,maxY=-Infinity;
    for(const [x,y] of coords){minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y)}
    return [minX,minY,maxX,maxY];
  };
  let viewport,scale,dpr;
  return {
    bounds:boundsFor,
    begin(view,w,h,ratio){
      scale=view.s;dpr=ratio;
      viewport=[view.x-w/(2*.767*scale),view.y-h/(2*scale),view.x+w/(2*.767*scale),view.y+h/(2*scale)];
      this.transform=[dpr*scale,0,0,dpr*scale,dpr*(w/2+(116-view.x)*.767*scale),dpr*(h/2+(view.y-40)*scale)];
    },
    stroke(coords,color,width,alpha=1,dashed=false){
      if(coords.length<2)return;
      let entry=cache.get(coords);
      if(!entry){entry={bounds:boundsFor(coords),path:null};cache.set(coords,entry)}
      const b=entry.bounds,v=viewport;
      if(b[2]<v[0]||b[0]>v[2]||b[3]<v[1]||b[1]>v[3])return;
      if(!entry.path){entry.path=new Path2D();coords.forEach(([x,y],i)=>{const px=(x-116)*.767,py=40-y;i?entry.path.lineTo(px,py):entry.path.moveTo(px,py)})}
      ctx.setTransform(...this.transform);ctx.strokeStyle=color;ctx.lineWidth=width/scale;ctx.globalAlpha=alpha;ctx.setLineDash(dashed?[5/scale,4/scale]:[]);ctx.stroke(entry.path);
    },
    finish(){ctx.setTransform(dpr,0,0,dpr,0,0);ctx.globalAlpha=1;ctx.setLineDash([])}
  };
}
