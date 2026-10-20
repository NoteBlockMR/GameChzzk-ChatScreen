package.path='obs-plugin/?.lua;'..package.path
local ffi=require('ffi')
local original_load=ffi.load
local raw_logs,sends,closes,warnings=0,0,0,0
-- Match OBS hook_error: it logs and returns normally, it DOES NOT throw.
_G.error=function()raw_logs=raw_logs+1 end
local fake={
 curl_easy_strerror=function()return 'Failed sending data to peer' end,
 curl_multi_init=function()return ffi.cast('void*',1)end,
 curl_multi_remove_handle=function()end,
 curl_easy_cleanup=function()closes=closes+1 end,
 curl_multi_cleanup=function()end,
 curl_ws_send=function()sends=sends+1;return 55 end,
 curl_ws_recv=function()return 81 end
}
ffi.load=function(name)if name=='libcurl' then return fake end;return original_load(name)end
local R=require('chzzk_receiver')
local r=R.new(function()warnings=warnings+1 end)
local now=1000;local oldtime=os.time;os.time=function()return now end
r.channel=string.rep('a',32)
r.net.easy=ffi.cast('void*',2);r.net.ws=true;r.net.queue={'test packet'};r.net.fragments=''
r:tick()
assert(sends==1 and closes==1 and warnings==1 and raw_logs==0)
assert(r.net.easy==nil and r.retry==1010)
for i=1,500 do r:tick()end
assert(sends==1 and warnings==1 and raw_logs==0)
local ok=pcall(require('chzzk_json').decode,'{invalid JSON')
assert(not ok and raw_logs==0)
os.time=oldtime;r:close()
-- A completed handshake must discard the total HTTP deadline before auth.
local cleared=false
fake.curl_easy_setopt=function(_,option,value)
 assert(option==155 and tonumber(value)==0);cleared=true;return 0
end
fake.curl_multi_perform=function()return 0 end
local completion=ffi.new('struct chzzk_curl_msg[1]')
completion[0].msg=1;completion[0].data.result=0
fake.curl_multi_info_read=function()return ffi.cast('struct chzzk_curl_msg*',completion) end
fake.curl_easy_getinfo=function(_,_,status)status[0]=101;return 0 end
local transport=require('chzzk_transport').new()
transport.easy=ffi.cast('void*',3);transport.websocket=true
transport.done=function()assert(cleared)end
transport:tick(function()end)
assert(cleared and transport.ws);transport:close()
ffi.load=original_load
print('OBS_ERROR_HOOK_OK: send55 closes once, 500 ticks no spam, malformed JSON raises')
