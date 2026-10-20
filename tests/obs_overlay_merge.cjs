const fs=require('fs'),vm=require('vm'),assert=require('assert');
const script=fs.readFileSync('obs-plugin/overlay.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
class Element{
 constructor(){this.children=[];this.style={};this.textContent=''}
 append(child){this.children.push(child)}
 replaceChildren(){this.children=[]}
}
async function scenario(soop){
 const feed=new Element(),pending=[];
 const states={CHZZK:{messages:[{key:'1',time:10,nickname:'동일 이름',content:'chzzk'}]},SOOP:{channel:'fixture_soop',messages:[{key:'1',time:20,nickname:'동일 이름',content:'<script>literal</script>'}]}};
 const calls=[];
 let now=100000;
 const context={Date:{now:()=>now},URLSearchParams,AbortSignal,location:{search:'?channel=test'+(soop?'&soop=fixture_soop':'')},
  document:{body:new Element(),querySelector:()=>feed,createElement:()=>new Element(),createTextNode:text=>({textContent:text})},
  setTimeout:fn=>pending.push(fn),fetch:async url=>{
   const platform=url.startsWith('http:')?'SOOP':'CHZZK';calls.push(platform);
   const state=states[platform];if(state instanceof Error)throw state;
   return {ok:true,json:async()=>state};
  }};
 vm.runInNewContext(script,context);
 const flush=async()=>{for(let i=0;i<10;i++)await Promise.resolve()};
 await flush();
 if(!soop){assert.deepEqual(calls,['CHZZK']);assert.equal(feed.children.length,1);return}
 assert.equal(feed.children.length,2);
 assert.equal(feed.children[0].children[0].children[0].textContent,'CHZZK');
 assert.equal(feed.children[1].children[0].children[0].textContent,'SOOP');
 assert.equal(feed.children[1].children[1].textContent,'<script>literal</script>');
 const cycle=async()=>{pending.splice(0).forEach(f=>f());await flush()};
 states.SOOP=new Error('offline');await cycle();assert.equal(feed.children.length,2);
 now+=30001;await cycle();assert.equal(feed.children.length,1);
 assert.equal(feed.children[0].children[1].textContent,'chzzk');
 states.SOOP={channel:'wrong',messages:[{key:'2',time:30,nickname:'wrong',content:'hidden'}]};await cycle();assert.equal(feed.children.length,1);
 states.SOOP.channel='fixture_soop';states.CHZZK.messages=[];await cycle();assert.equal(feed.children.length,1);
 assert.equal(feed.children[0].children[1].textContent,'hidden');
 states.CHZZK=new Error('offline');await cycle();assert.equal(feed.children.length,1);
 states.SOOP.messages=[{key:'d',time:40,nickname:'donor',content:'100',kind:'donation'},{key:'s',time:50,nickname:'sub',content:'6',kind:'subscription'}];
 await cycle();assert.equal(feed.children.length,2);
 assert(feed.children[0].className.includes('donation'));assert(feed.children[1].className.includes('subscription'));
 vm.runInNewContext("params.set('soop_donations','0');render()",context);assert.equal(feed.children.length,1);
 vm.runInNewContext("params.set('soop_subscriptions','0');render()",context);assert.equal(feed.children.length,0);
 vm.runInNewContext("params.delete('soop_donations');render()",context);assert.equal(feed.children.length,1);

}
(async()=>{await scenario(false);await scenario(true);console.log('MERGE_OK: optional addon, labels, time order, literal text, independent failure, mismatch, deletion')})().catch(e=>{console.error(e);process.exitCode=1});
