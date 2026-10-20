-- OBS replaces global error() with a log-only function. Keep failures catchable.
local function error(message) assert(false, message) end
-- Nonblocking HTTPS/WebSocket transport using OBS's own libcurl.
local ffi=require('ffi')
local bit=require('bit')
if not pcall(ffi.typeof, 'struct chzzk_curl_msg') then
ffi.cdef[[
void *curl_easy_init(void); void curl_easy_cleanup(void *);
int curl_easy_setopt(void *, int, ...); int curl_easy_getinfo(void *,int,...);
const char *curl_easy_strerror(int);
void *curl_multi_init(void); int curl_multi_cleanup(void *);
int curl_multi_add_handle(void *,void *); int curl_multi_remove_handle(void *,void *);
int curl_multi_perform(void *,int *);
struct chzzk_curl_msg { int msg; void *easy_handle; union {void *whatever; int result;} data;};
struct chzzk_curl_msg *curl_multi_info_read(void *,int *);
struct chzzk_ws_frame {int age; int flags; int64_t offset; int64_t bytesleft; size_t len;};
int curl_ws_recv(void *,void *,size_t,size_t *,const struct chzzk_ws_frame **);
int curl_ws_send(void *,const void *,size_t,size_t *,int64_t,unsigned int);
]]
end
local curl=ffi.load('libcurl')
local M={};M.__index=M
function M.new()
 return setmetatable({multi=assert(curl.curl_multi_init()),buffer=ffi.new('char[65536]'),n=ffi.new('size_t[1]'),meta=ffi.new('const struct chzzk_ws_frame *[1]'),running=ffi.new('int[1]'),remaining=ffi.new('int[1]')},M)
end
function M:clear()
 if self.easy then curl.curl_multi_remove_handle(self.multi,self.easy);curl.curl_easy_cleanup(self.easy);self.easy=nil end
 if self.callback then self.callback:free();self.callback=nil end
 self.ws=false;self.fragments='';self.queue={};self.active=nil
end
function M:start(url, websocket, done)
 self:clear();self.done=done;self.easy=assert(curl.curl_easy_init());self.websocket=websocket
 self.error_buffer=ffi.new('char[256]');self.stage=websocket and 'WebSocket' or 'HTTPS'
 local function opt(k,v) assert(curl.curl_easy_setopt(self.easy,k,v)==0,'curl option '..k) end
 opt(10010,ffi.cast('char*',self.error_buffer))
 opt(10002,url);opt(10018,'Mozilla/5.0 CHZZK-OBS-Lua/0.1')
 opt(99,ffi.new('long',1));opt(156,ffi.new('long',10000));opt(155,ffi.new('long',15000))
 -- TLS certificate and hostname verification retain libcurl secure defaults.
 if websocket then opt(141,ffi.new('long',2)) else
  self.body=''
  self.callback=ffi.cast('size_t(*)(char*,size_t,size_t,void*)',function(ptr,size,count)
   local n=tonumber(size*count)
   if #self.body+n>2097152 then return 0 end
   self.body=self.body..ffi.string(ptr,n);return n
  end)
  opt(20011,self.callback)
 end
 assert(curl.curl_multi_add_handle(self.multi,self.easy)==0)
end
function M:failure(operation,code)
 local detail=self.error_buffer and ffi.string(self.error_buffer) or ''
 if detail=='' then detail=ffi.string(curl.curl_easy_strerror(code)) end
 -- Native error diagnostics only: never dump packets, URLs or access tokens.
 detail=detail:gsub('[\r\n]',' '):sub(1,240)
 error(operation..' '..code..': '..detail)
end
function M:send(text)
 if #self.queue>=32 then error('outgoing queue overflow') end
 self.queue[#self.queue+1]=text
end
function M:tick(onmessage)
 if not self.easy then return end
 if not self.ws then
  curl.curl_multi_perform(self.multi,self.running)
  local msg=curl.curl_multi_info_read(self.multi,self.remaining)
  if msg~=nil and msg.msg==1 then
   local code=tonumber(msg.data.result)
   if code~=0 then self:failure(self.stage,code) end
   local status=ffi.new('long[1]');curl.curl_easy_getinfo(self.easy,0x200002,status)
   assert(tonumber(status[0])==(self.websocket and 101 or 200),'HTTP '..tonumber(status[0]))
   local done=self.done;self.done=nil
   if self.websocket then
    -- The 15s deadline applies only to HTTP/TLS upgrade. Schannel's
    -- connect-only send path still checks it after CURLMSG_DONE.
    -- Clear it before sending authentication or later heartbeat packets.
    assert(curl.curl_easy_setopt(self.easy,155,ffi.new('long',0))==0,'clear WebSocket handshake deadline')
    self.ws=true
   else local body=self.body;self:clear();done(body);return end
   done();return
  end
 else
  for _=1,8 do
   if not self.active and #self.queue>0 then self.active=table.remove(self.queue,1);self.sent=0 end
   if not self.active then break end
   local text=self.active
   self.n[0]=0
   -- Small JSON packets use a normal text frame; resume any partial write.
   local code=curl.curl_ws_send(self.easy,ffi.cast('const char*',text)+self.sent,#text-self.sent,self.n,0,1)
   self.sent=self.sent+tonumber(self.n[0])
   if code~=0 and code~=81 then self:failure('WebSocket send',code) end
   if self.sent==#text then self.active=nil end
   if code==81 then break end
  end
  for _=1,16 do
   local code=curl.curl_ws_recv(self.easy,self.buffer,65536,self.n,self.meta)
   if code==81 then break end
   if code~=0 then self:failure('WebSocket receive',code) end
   local meta=self.meta[0];local flags=tonumber(meta.flags)
   if bit.band(flags,8)~=0 then error('WebSocket closed') end
   if bit.band(flags,3)~=0 then
    self.fragments=self.fragments..ffi.string(self.buffer,self.n[0])
    assert(#self.fragments<=2097152,'Message too large')
    if meta.bytesleft==0 and bit.band(flags,4)==0 then
     local text=self.fragments;self.fragments='';onmessage(text)
    end
   end
  end
 end
end
-- libcurl invokes the write callback on this Lua/OBS timer thread.
jit.off(M.tick,true)
function M:close()self:clear();if self.multi then curl.curl_multi_cleanup(self.multi);self.multi=nil end end
return M
