// Run against the local FastAPI build. Playwright is loaded from NODE_PATH.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = 'http://127.0.0.1:8767';
const url = base + '/bigscreen/index.html';
const shots = process.env.PING_MAP_QA_SHOTS;
const panel = '#mapPanel';

async function shot(page, name) {
  if (shots) await page.screenshot({path:path.join(shots,name+'.png')});
}
function zoomReached(zoom) {
  const chart = window.echarts?.getInstanceByDom(document.querySelector('#mapBase'));
  return chart && Math.abs(chart.getOption().geo[0].zoom - zoom) < 1e-6;
}
function camera() {
  const chart = window.echarts.getInstanceByDom(document.querySelector('#mapBase'));
  const geo = chart.getOption().geo[0];
  const points = geo.boundingCoords.map(point => chart.convertToPixel({geoIndex:0}, point));
  return { points, bounds:geo.boundingCoords, zoom:geo.zoom, width:chart.getWidth(), height:chart.getHeight() };
}
function fits({points,width,height}) {
  const [[left,top],[right,bottom]] = points;
  assert(left>=8 && top>=8 && right<=width-8 && bottom<=height-8);
}
const fixture = [
  ['北京市','北京市',39.9042,116.4074,1], ['武汉市','湖北省',30.5928,114.3055,3],
  ['杭州市','浙江省',30.2741,120.1551,2], ['海口市','海南省',20.044,110.1999,1],
  ['离岛测试','海南省',9.9,114.3,1]
];
function makeSnapshot(extra = []) {
  const hosts = [...fixture,...extra].flatMap(([city,province,lat,lon,count])=>
    Array.from({length:count},(_,i)=>({name:city+' QA '+(i+1),city,province,latitude:lat,longitude:lon,
      avg_rtt:city==='海口市'?null:city==='杭州市'?52:0.2,packet_loss:city==='海口市'?100:0,is_online:city!=='海口市',enabled:true,
      status_type:city==='海口市'?'offline':'normal'})));
  return {host_status:hosts.map((h,i)=>({...h,id:i+1})),control_center:{
    name:'辽宁省 / 沈阳市',city:'沈阳市',longitude:123.43,latitude:41.80,isp:'测试线路'
  },screen_config:{refresh_interval:2}};
}
async function testHosts(page, extra = []) {
  const snapshot=makeSnapshot(extra);
  await page.route('**/api/public/datascreen?*',r=>r.fulfill({json:snapshot}));
}
async function cityTags(page) {
  return page.locator('.map-city-tag:visible').evaluateAll(tags=>tags.map(tag=>({
    name:tag.firstElementChild.textContent, count:Number(tag.lastElementChild.textContent),
    rect:tag.getBoundingClientRect().toJSON()
  })));
}
function noTagOverlap(tags) {
  for(const [i,{rect:a}] of tags.entries()) for(const {rect:b} of tags.slice(i+1)) {
    assert(a.right<=b.left || a.left>=b.right || a.bottom<=b.top || a.top>=b.bottom);
  }
}
async function wheel(page, direction, count) {
  await page.locator(panel).evaluate((element,[direction,count])=>{
    const r=element.getBoundingClientRect();
    for(let i=0;i<count;i++) element.dispatchEvent(new WheelEvent('wheel',{
      bubbles:true,cancelable:true,deltaY:direction,clientX:r.left+r.width/2,clientY:r.top+r.height/2
    }));
  },[direction,count]);
}
async function drag(page, dx, dy) {
  const r=await page.locator(panel).boundingBox();
  const x=r.x+r.width/2,y=r.y+r.height/2;
  await page.mouse.move(x,y);
  await page.mouse.down();
  await page.mouse.move(x+dx,y+dy,{steps:6});
  await page.mouse.up();
}
async function vector(page, width, height) {
  const mobile=width<=768;
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await testHosts(page);
  await page.addInitScript(()=>{
    window.mapPaints=0;
    const clear=CanvasRenderingContext2D.prototype.clearRect;
    CanvasRenderingContext2D.prototype.clearRect=function(...args){
      if(this.canvas.id==='mapFx') window.mapPaints++;
      return clear.apply(this,args);
    };
  });
  await page.goto(url);
  if(mobile) await page.locator('[data-mv=map]').click();
  await page.locator('#tierBadge.vec').waitFor({timeout:20000});
  await page.waitForFunction(zoomReached,1);
  const initial=await page.evaluate(camera);
  fits(initial);
  assert(initial.bounds[1][1]>=17.2 && initial.bounds[1][1]<=18.16);
  const projected=await page.evaluate(()=>{
    const chart = echarts.getInstanceByDom(document.querySelector('#mapBase'));
    const [,hainan]=chart.convertToPixel({geoIndex:0},[109.5,18.16]);
    const [,distant]=chart.convertToPixel({geoIndex:0},[113.9,10]);
    const geo=echarts.getMap('china-rt').geoJSON;
    const hainanPolygons=geo.features.find(f=>f.properties.name==='海南省').geometry.coordinates;
    return {hainan,distant,hainanPolygons:hainanPolygons.length};
  });
  assert(projected.hainan<initial.height-8 && projected.hainan>=initial.points[0][1]);
  assert(projected.distant>initial.points[1][1]);
  assert(projected.hainanPolygons>0 && projected.hainanPolygons<20);
  assert.equal(await page.locator('#mmLinks').count(),0);
  assert(await page.locator('#mapZoomOut').isDisabled());
  await page.waitForFunction(()=>window.mapPaints>0);
  await page.locator('.map-city-tag:visible').first().waitFor();
  const tags=await cityTags(page);
  noTagOverlap(tags);
  assert(tags.some(t=>t.name==='北京' && t.count===1));
  assert(tags.some(t=>t.name==='武汉' && t.count===3));
  assert(tags.some(t=>t.name==='海口' && t.count===1));
  assert(!tags.some(t=>t.name==='离岛测试'));
  assert(await page.locator('.map-city[data-pulse]').count()<= (mobile ? 3 : 5));
  await shot(page,`fit-${width}`);
  const paints=await page.evaluate(()=>window.mapPaints);
  await page.waitForTimeout(950);
  const idlePaints=await page.evaluate(()=>window.mapPaints)-paints;
  assert(idlePaints<=2,`Map painted ${idlePaints} times at rest`);

  const {rect}=(await cityTags(page)).find(t=>t.name==='武汉');
  if(mobile) await page.touchscreen.tap(rect.x+rect.width/2,rect.y+rect.height/2);
  else await page.mouse.move(rect.x+rect.width/2,rect.y+rect.height/2);
  const detail=mobile?'#mapSelection:not([hidden])':'#mapTip.on';
  await page.locator(detail).waitFor({timeout:3000}).catch(async error=>{
    const x=rect.x+rect.width/2,y=rect.y+rect.height/2;
    const target=await page.evaluate(([x,y])=>document.elementFromPoint(x,y)?.outerHTML.slice(0,250),[x,y]);
    throw new Error(width+'px: '+JSON.stringify({rect,target,tags:await cityTags(page),errors}),{cause:error});
  });
  if(mobile){
    assert.equal(await page.locator('#mapSelectionTitle').textContent(),'武汉');
    assert.equal(await page.locator('#mapSelectionHosts li').count(),3);
  }else assert.match(await page.locator('#tipName').textContent(),/^武汉市 QA [1-3]$/);
  if(mobile) await page.locator('#mapSelectionClose').tap();
  await page.mouse.move(0,0);

  if(mobile){
    const box=await page.locator(panel).boundingBox();
    const session=await page.context().newCDPSession(page);
    const dispatch=(type,d)=>session.send('Input.dispatchTouchEvent',{type,touchPoints:d ? [
      {id:1,x:box.x+box.width/2-d,y:box.y+box.height/2},
      {id:2,x:box.x+box.width/2+d,y:box.y+box.height/2}
    ]:[]});
    await dispatch('touchStart',20);
    for(const d of [32,48,62,85]) await dispatch('touchMove',d);
    await dispatch('touchEnd');
    await page.waitForFunction(zoomReached,3);
    await page.locator('#mapZoomReset').tap();
    await page.waitForFunction(zoomReached,1);
    await page.locator('[data-mv=overview]').click();
    await page.locator('[data-mv=map]').click();
    await page.waitForFunction(zoomReached,1);
    fits(await page.evaluate(camera));
  }else{
    await drag(page,1200,1000);
    assert.deepEqual(await page.evaluate(camera),initial);
    await wheel(page,-1,40);
    await page.waitForFunction(zoomReached,3);
    assert(await page.locator('#mapZoomIn').isDisabled());
    const zoomed=await page.evaluate(camera);
    for(const direction of [1,-1]){
      await drag(page,direction*1200,direction*1000);
      await page.waitForTimeout(80);
      const current=await page.evaluate(camera);
      const [[l,t],[r,b]]=current.points;
      assert(l<=12.5 && r>=current.width-12.5);
      assert(t<=149.5 && b>=current.height-40.5);
      assert.equal(current.zoom,3);
    }
    assert.notDeepEqual((await page.evaluate(camera)).points,zoomed.points);
    await shot(page,`bounded-${width}`);
    await wheel(page,1,40);
    await page.waitForFunction(zoomReached,1);
    assert.deepEqual(await page.evaluate(camera),initial);
    await page.locator('#mapFullscreen').click();
    await page.waitForFunction(()=>Boolean(document.fullscreenElement));
    await page.locator('.topbar').waitFor({state:'hidden'});
    await page.waitForFunction(()=>echarts.getInstanceByDom(document.querySelector('#mapBase')).getWidth()>innerWidth-6);
    fits(await page.evaluate(camera));
    await page.locator('#mapFullscreen').click();
    await page.waitForFunction(()=>!document.fullscreenElement);
    await page.locator('.topbar').waitFor();
  }
  assert.deepEqual(errors,[]);
  console.log(`${width}×${height}: full bounds, zoom limits, ${mobile?'pinch and tab switch':'clamped panning and fullscreen'}, ${idlePaints} idle map paints / 950ms`);
}

async function amapAdapter(browser) {
  const page=await browser.newPage({viewport:{width:1280,height:800}});
  try {
    await page.addInitScript(()=>localStorage.setItem('ping-amap-key','local-adapter-fixture'));
    await page.route('https://webapi.amap.com/maps?*',r=>r.fulfill({contentType:'text/javascript',body:`
      (()=>{
        const rad=Math.PI/180, merc=lat=>Math.log(Math.tan(Math.PI/4+lat*rad/2));
        window.AMap={LngLat:class{constructor(lng,lat){this.lng=lng;this.lat=lat;}},Map:class{
          constructor(host){
            this.host=host; this.listeners={}; this.center=[104.5,35.5]; this.zoom=4; this.cameras=[];
            host.classList.add('amap-container'); host.appendChild(document.createElement('canvas'));
            window.mapAdapter=this; setTimeout(()=>this.listeners.complete?.(),10);
          }
          on(name,fn){this.listeners[name]=fn;}
          setStatus(){}
          setZoomAndCenter(zoom,center,immediate){
            this.zoom=zoom; this.center=center; this.cameras.push({zoom,center,immediate});
            this.listeners.mapmove?.(); this.listeners.zoomchange?.();
          }
          lngLatToContainer(p){
            const scale=256*2**this.zoom/(2*Math.PI);
            return {x:this.host.clientWidth/2+(p.lng-this.center[0])*rad*scale,y:this.host.clientHeight/2+(merc(this.center[1])-merc(p.lat))*scale};
          }
          resize(){}
          destroy(){this.host.replaceChildren();}
        }};
      })();
    `}));
    await page.goto(url+'?map=amap');
    await page.locator('#tierBadge.amap').waitFor({timeout:14000});
    const fit=await page.evaluate(()=>window.mapAdapter.cameras.at(-1));
    assert(fit.immediate);
    await wheel(page,-1,25);
    await page.waitForFunction(z=>Math.abs(window.mapAdapter.zoom-z)<1e-6,fit.zoom+Math.log2(3));
    await drag(page,1500,1200);
    const zoomed=await page.evaluate(()=>window.mapAdapter.cameras.at(-1));
    assert(zoomed.center[0]>=73.2 && zoomed.center[0]<=135.6);
    assert(zoomed.center[1]>=17.2 && zoomed.center[1]<=53.9);
    await page.locator('#mapZoomReset').click();
    await page.waitForFunction(z=>Math.abs(window.mapAdapter.zoom-z)<1e-6,fit.zoom);
    assert.deepEqual(await page.evaluate(()=>window.mapAdapter.cameras.at(-1)),fit);
    console.log('AMap adapter: mocked SDK, fit-relative zoom cap, bounded drag and reset');
  }finally{await page.close();}
}

async function missingMapAsset(browser) {
  const page=await browser.newPage({viewport:{width:1280,height:800}});
  try{
    await page.route(/\/echarts(?:\.min)?\.js(?:\?|$)/,r=>r.abort());
    await page.goto(url);
    await page.getByText('地图资源暂不可用').waitFor();
    assert.equal(await page.locator('#mapBase canvas').count(),0);
    assert.equal(await page.locator('#mapHub').isVisible(),false);
    assert(await page.locator('#mapZoomOut').isDisabled());
    console.log('Missing local map runtime: explicit failure, no replacement silhouette');
  }finally{await page.close();}
}

async function denseCities(browser) {
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  try{
    await testHosts(page,[
      ['上海市','上海市',31.23,121.47,8], ['苏州市','江苏省',31.30,120.58,4],
      ['无锡市','江苏省',31.57,120.30,5], ['南京市','江苏省',32.06,118.79,6],
      ['宁波市','浙江省',29.87,121.55,3], ['合肥市','安徽省',31.82,117.22,1],
      ['广州市','广东省',23.13,113.27,7], ['深圳市','广东省',22.54,114.06,4],
      ['成都市','四川省',30.57,104.07,3], ['西安市','陕西省',34.34,108.94,3],
      ['兰州市','甘肃省',36.06,103.83,2], ['乌鲁木齐市','新疆维吾尔自治区',43.79,87.62,1]
    ]);
    await page.goto(url);
    await page.locator('#tierBadge.vec').waitFor();
    await page.waitForFunction(zoomReached,1);
    const tag=page.locator('.map-city-tag:visible').first();
    await tag.waitFor();
    const tags=await cityTags(page);
    assert(tags.length>=7 && tags.length<=14);
    noTagOverlap(tags);
    assert(tags.some(t=>t.name==='上海' && t.count===8));
    assert(tags.some(t=>t.name==='乌鲁木齐' && t.count===1));
    const hasMotion=await page.locator('.map-city[data-pulse] .map-city-ring').first().evaluate(el=>
      getComputedStyle(el,'::after').animationName !== 'none');
    assert.equal(hasMotion,false);
    await shot(page,'dense-1440');
    console.log('Dense city fixture: '+tags.length+' separated labels; reduced-motion respected');
  }finally{await page.close();}
}

async function stableStartup(browser, width, height) {
  const mobile=width<768;
  const page=await browser.newPage({viewport:{width,height},isMobile:mobile,hasTouch:mobile});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  try{
    let resume, version=0;
    let gate=new Promise(r=>{resume=r;});
    const snapshot=makeSnapshot();
    snapshot.host_status.push(
      {id:90,name:'停用节点',province:'湖北省',city:'宜昌市',enabled:false,is_online:true,avg_rtt:1,packet_loss:0},
      {id:91,name:'未检测节点',province:'湖北省',city:'武汉市',enabled:true,is_online:false,avg_rtt:null,packet_loss:null}
    );
    snapshot.screen_config.refresh_interval=1;
    const external=[];
    page.on('request',r=>{if(!r.url().startsWith(base) && /echarts|china.json|amap/.test(r.url())) external.push(r.url());});
    await page.route('**/api/public/datascreen?*',async r=>{
      await gate;
      if(version===2) return r.fulfill({status:503,json:{detail:'fixture unavailable'}});
      const data=structuredClone(snapshot);
      if(version===1) data.host_status.find(n=>n.name==='武汉市 QA 1').avg_rtt=10;
      return r.fulfill({json:data});
    });
    await page.goto(url);
    if(mobile) await page.locator('[data-mv=map]').tap();
    await page.locator('#mapBase.on').waitFor();
    const initial=await page.evaluate(camera);
    assert.equal(await page.locator('#mapHub').isVisible(),false);
    assert.equal(await page.locator('#mapSignal').isVisible(),false);
    assert(await page.locator('.map-scan-travel').isVisible());
    assert.equal(await page.locator('#rankList .rank-row').count(),0);
    assert.equal(await page.locator('.map-city-tag').count(),0);
    assert.equal(await page.locator('#hudAvg').textContent(),'—');
    await shot(page,'map-first-'+width);
    resume();
    await page.locator('#mapHub:visible').waitFor();
    assert.deepEqual(await page.evaluate(camera),initial);
    assert.equal(await page.locator('#chipHub').textContent(),'沈阳');
    assert.match(await page.locator('#mapHub').textContent(),/沈阳/);
    const hubError=await page.locator('#mapHub').evaluate(el=>{
      const base=document.querySelector('#mapBase'), chart=echarts.getInstanceByDom(base);
      const [x,y]=chart.convertToPixel({geoIndex:0},[123.43,41.8]);
      const r=el.getBoundingClientRect(), b=base.getBoundingClientRect();
      return Math.hypot(r.x+r.width/2-b.x-x,r.y+r.height/2-b.y-y);
    });
    assert(hubError<1);
    const click=mobile?page.touchscreen.tap.bind(page.touchscreen):page.mouse.click.bind(page.mouse);
    const points=async(lng,lat)=>page.evaluate(([lng,lat])=>{
      const el=document.querySelector('#mapBase'),chart=echarts.getInstanceByDom(el),r=el.getBoundingClientRect();
      const [x,y]=chart.convertToPixel({geoIndex:0},[lng,lat]); return [x+r.x,y+r.y];
    },[lng,lat]);
    await page.locator('#mapHub').click();
    assert.equal(await page.locator('#mapSelectionKind').textContent(),'控制中心');
    await page.locator('#mapSelectionClose').click();
    // At narrow widths the Wuhan label can legitimately cover a province coordinate.
    const provincePoint=await page.evaluate(()=>{
      const el=document.querySelector('#mapBase'), chart=echarts.getInstanceByDom(el), bounds=el.getBoundingClientRect();
      const geo=chart.getModel().getComponent('geo').coordinateSystem;
      const tags=[...document.querySelectorAll('.map-city-tag,#mapHub span')]
        .filter(tag=>getComputedStyle(tag).visibility==='visible').map(tag=>tag.getBoundingClientRect());
      for(let lat=33.2;lat>29.0;lat-=.15){
        for(let lon=108.8;lon<116.3;lon+=.15){
          if(geo.getRegionByCoord([lon,lat])?.name!=='湖北省') continue;
          const [x,y]=chart.convertToPixel({geoIndex:0},[lon,lat]);
          const a=x+bounds.x,b=y+bounds.y;
          if(tags.some(r=>a>r.left-5 && a<r.right+5 && b>r.top-5 && b<r.bottom+5)) continue;
          const [wx,wy]=chart.convertToPixel({geoIndex:0},[114.3055,30.5928]);
          if(Math.hypot(x-wx,y-wy)>11) return [a,b];
        }
      }
    });
    assert(provincePoint);
    await page.locator(panel).evaluate(el=>{
      el.addEventListener('pointerup',()=>document.body.classList.remove('lite'),{once:true,capture:true});
      new MutationObserver((entries,observer)=>{
        if(entries.some(e=>[...e.addedNodes].some(n=>n.classList?.contains('map-ripple')))){
          window.rippleStarted=true; observer.disconnect();
        }
      }).observe(el,{childList:true});
    });
    await click(...provincePoint);
    assert(await page.evaluate(()=>window.rippleStarted));
    await page.locator('#mapSelection:visible').waitFor();
    assert.equal(await page.locator('#mapSelectionTitle').textContent(),'湖北省');
    const highlighted=await page.evaluate(()=>{
      const el=document.querySelector('#mapBase'), chart=echarts.getInstanceByDom(el);
      return chart.getModel().getComponent('geo').isSelected('湖北省');
    });
    assert(highlighted);
    const rows=page.locator('#mapSelectionHosts');
    assert.match(await rows.textContent(),/已停用/);
    assert.match(await rows.textContent(),/未检测/);
    assert.match(await rows.textContent(),/0.2 ms/);
    await page.locator('.map-ripple').waitFor({state:'detached'});
    await shot(page,'province-selected-'+width);
    version=1;
    await rows.getByRole('button',{name:/武汉市 QA 1.*10.0 ms/}).waitFor();
    assert.equal(await page.locator('#mapSelectionTitle').textContent(),'湖北省');
    assert.deepEqual(await page.evaluate(camera),initial);
    await rows.getByRole('button',{name:/武汉市 QA 1/}).click();
    assert.match(await page.locator('#mapSelectionSummary').textContent(),/10.0 ms/);
    await page.locator('#mapSelectionClose').click();
    await click(...await points(87.6,43.6));
    assert.match(await page.locator('#mapSelectionSummary').textContent(),/暂无监控主机/);
    await page.locator('#mapSelectionClose').click();
    await shot(page,'map-with-hosts-'+width);
    version=2;
    await page.getByText('连接中断',{exact:false}).waitFor();
    assert.deepEqual(await page.evaluate(camera),initial);
    assert(await page.locator('#mapHub').isVisible());
    // Cold/hot reload with another blocked snapshot: no stale host labels or alternate map.
    gate=new Promise(r=>{resume=r;}); version=0;
    await page.reload();
    await page.locator('#mapBase.on').waitFor();
    assert.deepEqual(await page.evaluate(camera),initial);
    assert.equal(await page.locator('#mapHub').isVisible(),false);
    assert.equal(await page.locator('.map-city-tag').count(),0);
    resume();
    await page.locator('#mapHub:visible').waitFor();
    assert.deepEqual(external,[]);
    assert.deepEqual(errors,[]);
    console.log(width+'px startup: map first, exact statuses and center, province selection, live update, outage and reload');
  }finally{await page.close();}
}

async function compactRegions(browser,width,height){
  const mobile=width<768;
  const page=await browser.newPage({viewport:{width,height},isMobile:mobile,hasTouch:mobile});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  try{
    await testHosts(page,[
      ['香港','香港特别行政区',22.3193,114.1694,3],
      ['九龙','香港特别行政区',22.324,114.1698,2],
      ['澳门','澳门特别行政区',22.1987,113.5439,2],
      ['深圳市','广东省',22.5431,114.0579,4],
      ['珠海市','广东省',22.271,113.5767,2],
      ['天津市','天津市',39.08,117.2,2],
      ['上海市','上海市',31.23,121.47,4]
    ]);
    await page.goto(url);
    if(mobile) await page.locator('[data-mv=map]').tap();
    await page.locator('#mapBase.on').waitFor();
    const badges=page.locator('[data-compact] .map-city-tag:visible');
    await badges.getByText('香港',{exact:true}).waitFor();
    const tags=await cityTags(page);
    noTagOverlap(tags);
    for(const [name,count] of [['香港',5],['澳门',2],['北京',1],['天津',2],['上海',4]]){
      assert(tags.some(t=>t.name===name && t.count===count),width+'px missing '+name+': '+JSON.stringify(tags.map(t=>t.name)));
    }
    assert.equal(await page.locator('[data-compact] .map-city-leader:visible').count(),5);
    const focus=page.locator('#mapRegionFocus');
    const hongKong=page.getByRole('button',{name:'香港，5 台主机'});
    if(!mobile){
      await hongKong.hover();
      await page.waitForFunction(()=>document.querySelector('#mapRegionFocus').dataset.region==='香港特别行政区');
      assert((await focus.locator('path').getAttribute('d')).startsWith('M'));
      await shot(page,'compact-hover-'+width);
    }else await shot(page,'compact-'+width);
    await (mobile?hongKong.tap():hongKong.press('Enter'));
    assert.equal(await page.locator('#mapSelectionTitle').textContent(),'香港');
    assert.equal(await page.locator('#mapSelectionHosts li').count(),5);
    assert.equal(await hongKong.getAttribute('aria-pressed'),'true');
    assert(await page.evaluate(()=>echarts.getInstanceByDom(document.querySelector('#mapBase')).getModel().getComponent('geo').isSelected('香港特别行政区')));
    if(!mobile){
      const province=await page.evaluate(()=>{
        const el=document.querySelector('#mapBase'), chart=echarts.getInstanceByDom(el), r=el.getBoundingClientRect();
        const [x,y]=chart.convertToPixel({geoIndex:0},[101.77,36.6]);return [x+r.x,y+r.y];
      });
      await page.mouse.move(...province);
      await page.waitForFunction(()=>document.querySelector('#mapRegionFocus').dataset.region==='青海省');
      await shot(page,'province-hover-'+width);
      await page.mouse.move(0,0);
      assert.equal(await focus.getAttribute('data-region'),null);
      assert.equal(await page.locator('#mapSelectionTitle').textContent(),'香港');
    }
    await shot(page,'compact-selected-'+width);
    await page.locator('#mapSelectionClose').click();
    const hub=page.locator('#mapHub');
    const signal=page.locator('#mapSignal');
    assert.equal(await signal.locator('.hub-wave').count(),2);
    // Keep the normal CSS, force the low-FPS state and freeze a pair of real animation frames.
    const motion=await page.evaluate(()=>{
      document.body.classList.add('lite');
      const hub=document.querySelector('#mapHub'), signal=document.querySelector('#mapSignal');
      const scan=document.querySelector('.map-scan-travel');
      const waves=[...signal.querySelectorAll('.hub-wave')];
      const breath=hub.getAnimations({subtree:true}).find(a=>a.animationName==='hubBreathe');
      function at(animation,time){animation.pause();animation.currentTime=time;}
      at(breath,0);
      const peak=()=>Number(getComputedStyle(hub.querySelector('.hub-core'),'::before').opacity);
      const dim=peak(); at(breath,1600);
      const bright=peak();
      const scanMotion=scan.getAnimations()[0];
      at(scanMotion,1000);
      const scanBefore=new DOMMatrix(getComputedStyle(scan).transform).f;
      at(scanMotion,2900);
      const scanAfter=new DOMMatrix(getComputedStyle(scan).transform).f;
      const radii=waves.map((wave,i)=>{
        at(wave.getAnimations()[0],i===0?1300:4600+650-3950);
        const r=wave.getBoundingClientRect(), h=hub.getBoundingClientRect();
        return {radius:r.width/2,originError:Math.hypot(r.x+r.width/2-h.x-h.width/2,r.y+r.height/2-h.y-h.height/2)};
      });
      return {dim,bright,scanBefore,scanAfter,radii};
    });
    assert(motion.bright-motion.dim>.35);
    assert(motion.scanAfter-motion.scanBefore>20);
    assert(motion.radii[0].radius>motion.radii[1].radius+12);
    assert(motion.radii.every(r=>r.radius>25 && r.originError<1));
    await shot(page,'map-motion-'+width);
    await page.emulateMedia({reducedMotion:'reduce'});
    assert.equal(await signal.isVisible(),false);
    assert.equal(await page.locator('.map-scan-travel').isVisible(),false);
    assert(await hub.isVisible());
    await hub.click();
    assert.equal(await page.locator('#mapSelectionKind').textContent(),'控制中心');
    assert.deepEqual(errors,[]);
    console.log(width+'px compact regions: five readable callouts, province hover/selection, grouped hosts, and center motion preference');
  }finally{await page.close();}
}

async function disabledMotion(browser){
  const page=await browser.newPage({viewport:{width:1280,height:800}});
  try{
    const snapshot=makeSnapshot(); snapshot.screen_config.enable_animation=false;
    await page.route('**/api/public/datascreen?*',r=>r.fulfill({json:snapshot}));
    await page.goto(url);
    const hub=page.locator('#mapHub:visible');
    await hub.waitFor();
    assert.equal(await page.locator('#mapMotion').isVisible(),false);
    assert.equal(await hub.locator('.hub-core').evaluate(el=>getComputedStyle(el,'::before').animationName),'none');
    console.log('Animation setting off: static hub, no scan, waves or breathing');
  }finally{await page.close();}
}

(async()=>{
  if(shots) fs.mkdirSync(shots,{recursive:true});
  const browser=await chromium.launch();
  try{
    for(const [width,height] of [[1440,900],[1280,800],[390,844],[320,640]]){
      const page=await browser.newPage({viewport:{width,height},isMobile:width<768,hasTouch:width<768});
      try{await vector(page,width,height);}finally{await page.close();}
    }
    await missingMapAsset(browser);
    await amapAdapter(browser);
    await denseCities(browser);
    await stableStartup(browser,1920,945);
    await stableStartup(browser,1440,900);
    await stableStartup(browser,390,844);
    await compactRegions(browser,1920,945);
    await compactRegions(browser,390,844);
    await disabledMotion(browser);
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
