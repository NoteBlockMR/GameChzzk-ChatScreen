local json=require('chzzk_json')
local Transport=require('chzzk_transport')
local R={};R.__index=R
local function decode(value)
 if type(value)=='table' then return value end
 if type(value)=='string' then local ok,v=pcall(json.decode,value);if ok and type(v)=='table' then return v end end
 return {}
end
local function valid_id(value)return type(value)=='string' and #value>0 and #value<257 end
function R.channel(value)
 local id=value:match('^%s*([%da-fA-F]+)%s*$') or value:match('^https://chzzk%.naver%.com/live/([%da-fA-F]+)') or value:match('^https://chzzk%.naver%.com/([%da-fA-F]+)')
 if id and #id==32 then return id:lower() end
end
function R.new(log)
 return setmetatable({channel=false,net=Transport.new(),messages={},purged={},deleted={},status='대기',log=log or print,retry=0,last=0},R)
end
function R:packet(cmd,body,extra)
 local p={cmd=cmd,ver='2',svcid='game',cid=self.cid,bdy=body}
 for k,v in pairs(extra or {})do p[k]=v end
 self.net:send(json.encode(p))
end
function R:start(channel)
 assert(R.channel(channel),'올바른 채널 주소 / ID를 입력하세요.')
 if self.channel==R.channel(channel) then return end
 self.channel=R.channel(channel);self.retry=0;self.failures=0;self.last_error=nil;self.last_error_at=nil;self.messages={};self.purged={};self.deleted={};self:connect()
end
function R:connect()
 self.status='연결 중';self.messages={};self.last=os.time();self.connected_at=nil;self.ping=os.time()
 self.net:start('https://api.chzzk.naver.com/polling/v2/channels/'..self.channel..'/live-status',false,function(raw)
  local content=decode(raw).content
  assert(type(content)=='table' and valid_id(content.chatChannelId),'방송 채팅을 찾을 수 없습니다.')
  self.cid=content.chatChannelId
  assert(self.cid:match('^[%w_-]+$'),'Invalid chat channel')
  self.net:start('https://comm-api.game.naver.com/nng_main/v1/chats/access-token?channelId='..self.cid..'&chatType=STREAMING',false,function(tokenraw)
   local token=decode(tokenraw).content
   assert(type(token)=='table' and type(token.accessToken)=='string','채팅 토큰 발급 실패')
   local sum=0;for i=1,#self.cid do sum=sum+self.cid:byte(i) end
   self.net:start('wss://kr-ss'..(sum%9+1)..'.chat.naver.com/chat',true,function()
    self:packet(100,{accTkn=token.accessToken,auth='READ',devType=2001},{tid=1})
   end)
  end)
 end)
end
function R:purge(user)
 if valid_id(user) then self.purged[user]=os.time()*1000+999 end
end
function R:receive(raw)
 local p=decode(raw);local b=decode(p.bdy);local cmd=p.cmd
 self.last=os.time()
 if cmd==0 then self.net:send('{"cmd":10000,"ver":"2"}');return end
 if cmd==10100 then
  assert(type(b.sid)=='string','채팅 인증 실패');self.status='연결됨';self.connected_at=os.time();self.sid=b.sid
  self:packet(5101,{recentMessageCount=50},{sid=b.sid,tid=2});return
 end
 if cmd==93101 or cmd==93102 or cmd==15101 then
  for _,m in ipairs(b.messageList or b) do
   local profile=decode(m.profile);local user=m.uid or m.userId or profile.userIdHash
   local stamp=m.msgTime or m.messageTime;local content=m.msg or m.content
   local status=m.msgStatusType or m.messageStatusType
   if valid_id(user) and type(stamp)=='number' and type(content)=='string' and type(profile.nickname)=='string' and (not status or status=='NORMAL') then
    local key=user..':'..string.format('%.0f',stamp);local found=false
    for _,old in ipairs(self.messages)do if old.key==key then found=true;break end end
    if not found then self.messages[#self.messages+1]={key=key,user=user,time=stamp,nickname=profile.nickname,content=content} end
   end
  end
  table.sort(self.messages,function(a,b)return a.time<b.time end)
  while #self.messages>100 do table.remove(self.messages,1) end
 elseif cmd==94015 and (b.penaltyType=='BAN' or b.penaltyType=='MUTE') then self:purge(b.userId)
 elseif cmd==94005 then for _,id in ipairs(b.quitUserIdList or {})do self:purge(id) end
 elseif cmd==93006 and (b.type=='TEMPORARY_RESTRICT' or b.type=='RESTRICT_USER') then self:purge(b.userIdHash)
 elseif cmd==94008 and valid_id(b.userId) and type(b.messageTime)=='number' then
  local key=b.userId..':'..string.format('%.0f',b.messageTime)
  if b.blindType=='CANCEL' then self.deleted[key]=nil
  elseif b.blindType=='BLIND' or b.blindType=='HIDDEN' or b.blindType=='RECLAIM' or b.blindType=='FILTERED' or b.blindType=='CBOTBLIND' then self.deleted[key]=true end
 end
end
function R:snapshot()
 local visible={}
 for _,m in ipairs(self.messages)do
  if not self.deleted[m.key] and not (self.purged[m.user] and m.time<=self.purged[m.user])then visible[#visible+1]=m end
 end
 -- json.lua treats an empty table as an array.
 return json.encode({channel=self.channel or '',messages=visible,status=self.status})
end
function R:tick()
 if not self.channel then return end
 if os.time()<self.retry then return end
 local ok,err=pcall(function()
  if not self.net.easy then self:connect() end
  self.net:tick(function(raw)self:receive(raw)end)
  if self.status=='연결됨' then
   assert(os.time()-self.last<70,'채팅 응답 시간 초과')
   if os.time()-(self.ping or 0)>20 then self.net:send('{"cmd":0,"ver":"2"}');self.ping=os.time() end
  end
 end)
 if not ok then
  self.net:clear();self.messages={};self.status='재연결 대기'
  self.failures=math.min((self.failures or 0)+1,4)
  local delay=math.min(10*2^(self.failures-1),60)
  local now=os.time();self.retry=now+delay
  local message=tostring(err):gsub('^.-:%d+: ','')
  if message~=self.last_error or now-(self.last_error_at or 0)>=60 then
   self.log('CHZZK 연결 오류: '..message..' ('..delay..'초 후 재연결, 동일 오류 로그는 60초 간격)')
   self.last_error=message;self.last_error_at=now
  end
 elseif self.connected_at and os.time()-self.connected_at>=60 then
  self.failures=0
 end
end
function R:close()self.net:close();self.messages={} end
return R
