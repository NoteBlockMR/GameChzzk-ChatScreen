package.path='obs-plugin/?.lua;'..package.path
local count,attempts=0,0
package.loaded.chzzk_transport={new=function()return {easy=true,tick=function()attempts=attempts+1;error('WebSocket send 55')end,clear=function()end,close=function()end}end}
local R=require('chzzk_receiver')
local r=R.new(function()count=count+1 end);r.channel=string.rep('a',32)
local original=os.time;local now=1000;os.time=function()return now end
r:tick();assert(count==1 and attempts==1 and r.retry==1010)
for _=1,100 do r:tick()end;assert(count==1 and attempts==1)
now=1010;r:tick();assert(count==1 and r.retry==1030)
now=1030;r:tick();assert(count==1 and r.retry==1070)
now=1070;r:tick();assert(count==2 and r.retry==1130)
os.time=original;r:close()
print('RETRY_OK: failed socket paused, exponential backoff, duplicate log throttled')
