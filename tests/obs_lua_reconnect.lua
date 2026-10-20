package.path='obs-plugin/?.lua;'..package.path
local json=require('chzzk_json')
local now=1000
local original=os.time;os.time=function()return now end
local logs,starts={},0
local net={easy=true,fail=true}
function net:clear()self.easy=nil end
function net:close()self:clear()end
function net:send()end
function net:start(url,ws,done)
 self.easy=true;starts=starts+1
 if ws then done()
 elseif url:find('live-status',1,true) then done('{"content":{"chatChannelId":"test"}}')
 else done('{"content":{"accessToken":"test"}}') end
end
function net:tick(receive)
 if self.fail then self.fail=false;assert(false,'WebSocket receive 56: Recv failure: Connection was reset')end
 receive('{"cmd":10100,"bdy":{"sid":"test"}}')
 receive(json.encode({cmd=93101,bdy={{uid='user',msgTime=now*1000,msg='resumed',profile={nickname='test'}}}}))
end
package.loaded.chzzk_transport={new=function()return net end}
local r=require('chzzk_receiver').new(function(message,level)logs[#logs+1]={message,level}end)
r.channel=string.rep('a',32);r.status='연결됨'
r:tick()
assert(r.status=='재연결 대기' and r.retry==1010 and not net.easy)
assert(#logs==1 and logs[1][1]:find('receive 56',1,true))
now=1009;r:tick();assert(starts==0)
now=1010;r:tick()
assert(starts==3 and r.status=='연결됨' and #r.messages==1)
assert(#logs==2 and logs[2][2]=='info' and logs[2][1]:find('재연결 완료',1,true))
r:tick();assert(#logs==2,'duplicate authentication must not repeat recovery log')
r:close();os.time=original
print('RECONNECT_OK: receive 56 closes socket, waits, authenticates again, resumes chat and logs recovery once')
