package.path='obs-plugin/?.lua;'..package.path
local json=require('chzzk_json')
-- Protocol tests do not contact the network.
package.loaded.chzzk_transport={new=function()return {send=function()end,close=function()end}end}
local R=require('chzzk_receiver')
local r=R.new();local time=os.time()*1000-10000
local function chat(user,stamp,text)
 r:receive(json.encode({cmd=93101,bdy={{uid=user,msgTime=stamp,msg=text,profile=json.encode({nickname='same nickname'}),msgStatusType='NORMAL'}}}))
end
local function count()return #json.decode(r:snapshot()).messages end
chat('a',time,'<script>literal</script>');chat('b',time,'hello');chat('a',time,'duplicate');assert(count()==2)
r:receive(json.encode({cmd=94015,bdy={penaltyType='BAN',userId='a'}}));assert(count()==1)
chat('a',time+1,'late history');assert(count()==1)
chat('a',os.time()*1000+2000,'future');assert(count()==2)
r:receive(json.encode({cmd=94008,bdy={userId='b',messageTime=time,blindType='BLIND'}}));assert(count()==1)
r:receive(json.encode({cmd=94008,bdy={userId='b',messageTime=time,blindType='CANCEL'}}));assert(count()==2)
r:receive(json.encode({cmd=94005,bdy={quitUserIdList={'b'}}}));assert(count()==1)
r:receive('malformed');assert(count()==1)
for i=1,150 do chat('new',time+i,'message')end
assert(#r.messages==100)
assert(R.channel('https://chzzk.naver.com/live/'..string.rep('a',32))==string.rep('a',32))
assert(not R.channel('https://evil.example/'..string.rep('a',32)))
r:close();print('LUA_PROTOCOL_OK: dedup, ban, kick, late history, blind/undo, bounds, channel validation')
