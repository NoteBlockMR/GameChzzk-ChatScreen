-- OBS replaces global error() with a log-only function. Keep failures catchable.
local function error(message) assert(false, message) end
-- Small bounded nonblocking HTTP server. Loopback only; read-only endpoints.
local ffi=require('ffi')
ffi.cdef[[
int WSAStartup(unsigned short,void*); int WSACleanup(void); int WSAGetLastError(void);
uintptr_t socket(int,int,int); int closesocket(uintptr_t);
int ioctlsocket(uintptr_t,long,unsigned long*);
struct chzzk_addr {unsigned short family; unsigned short port; unsigned int addr;char zero[8];};
unsigned short htons(unsigned short); unsigned int inet_addr(const char*);
int bind(uintptr_t,const struct chzzk_addr*,int);int listen(uintptr_t,int);
uintptr_t accept(uintptr_t,void*,void*);int recv(uintptr_t,char*,int,int);int send(uintptr_t,const char*,int,int);
]]
local ws=ffi.load('Ws2_32')
local invalid=ffi.cast('uintptr_t',-1)
local M={};M.__index=M
function M.new(html,snapshot,port)
 local data=ffi.new('char[512]');assert(ws.WSAStartup(0x202,data)==0,'WSAStartup')
 local self=setmetatable({clients={},html=html,snapshot=snapshot,port=port or 18766,buf=ffi.new('char[8192]')},M)
 self.socket=ws.socket(2,1,6)
 local a=ffi.new('struct chzzk_addr');a.family=2;a.port=ws.htons(self.port);a.addr=ws.inet_addr('127.0.0.1')
 local nb=ffi.new('unsigned long[1]',1)
 if self.socket==invalid or ws.bind(self.socket,a,16)~=0 or ws.listen(self.socket,8)~=0 or ws.ioctlsocket(self.socket,-2147195266,nb)~=0 then
  self:close();error('로컬 포트 '..self.port..'를 열 수 없습니다. 중복 스크립트를 확인하세요.')
 end
 return self
end
function M:tick()
 for _=1,4 do
  local s=ws.accept(self.socket,nil,nil);if s==invalid then break end
  if #self.clients>=16 then ws.closesocket(s) else
   ws.ioctlsocket(s,-2147195266,ffi.new('unsigned long[1]',1))
   self.clients[#self.clients+1]={socket=s,request='',at=os.time(),offset=0}
  end
 end
 for i=#self.clients,1,-1 do
  local c=self.clients[i];local close=os.time()-c.at>5
  if not close and not c.response then
   local n=ws.recv(c.socket,self.buf,8192,0)
   if n>0 then c.request=c.request..ffi.string(self.buf,n)
   elseif n==0 or ws.WSAGetLastError()~=10035 then close=true end
   if #c.request>8192 then close=true end
   if c.request:find('\r\n\r\n',1,true) then
    local path=c.request:match('^GET ([^ ]+) HTTP/1%.[01]\r\n')
    local host=c.request:lower():match('\r\nhost:%s*([^\r\n]+)')
    local status,mime,body='200 OK','application/json; charset=utf-8',''
    if host~='127.0.0.1:'..self.port and host~='localhost:'..self.port then status='403 Forbidden'
    elseif path=='/' or (path and path:sub(1,2)=='/?')then mime='text/html; charset=utf-8';body=self.html
    elseif path=='/state' or (path and path:sub(1,7)=='/state?')then body=self.snapshot()
    else status='404 Not Found' end
    c.response='HTTP/1.1 '..status..'\r\nContent-Type: '..mime..'\r\nCache-Control: no-store\r\nConnection: close\r\nContent-Length: '..#body..'\r\n\r\n'..body
   end
  end
  if c.response and not close then
   local n=ws.send(c.socket,ffi.cast('const char*',c.response)+c.offset,math.min(65536,#c.response-c.offset),0)
   if n>0 then c.offset=c.offset+n elseif ws.WSAGetLastError()~=10035 then close=true end
   if c.offset>=#c.response then close=true end
  end
  if close then ws.closesocket(c.socket);table.remove(self.clients,i) end
 end
end
function M:close()
 for _,c in ipairs(self.clients)do ws.closesocket(c.socket)end;self.clients={}
 if self.socket and self.socket~=invalid then ws.closesocket(self.socket);self.socket=nil end
 ws.WSACleanup()
end
return M
