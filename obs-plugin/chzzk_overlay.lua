-- Windows-only controller for a projector created by this script.
local ffi=require('ffi');local bit=require('bit')
if not pcall(ffi.typeof,'chzzk_enum_windows') then ffi.cdef[[
 typedef int (__stdcall *chzzk_enum_windows)(void*,intptr_t);
 int EnumWindows(chzzk_enum_windows,intptr_t);int IsWindow(void*);
 unsigned long GetWindowThreadProcessId(void*,unsigned long*);unsigned long GetCurrentProcessId(void);
 int GetWindowTextW(void*,uint16_t*,int);
 intptr_t GetWindowLongPtrW(void*,int);intptr_t SetWindowLongPtrW(void*,int,intptr_t);
 int SetWindowPos(void*,void*,int,int,int,int,unsigned int);
 int SetLayeredWindowAttributes(void*,unsigned long,unsigned char,unsigned long);
 int ShowWindow(void*,int);int IsWindowVisible(void*);
 int SetPropW(void*,const uint16_t*,void*);void *GetPropW(void*,const uint16_t*);void *RemovePropW(void*,const uint16_t*);
 ]] end
local user=ffi.load('user32');local kernel=ffi.load('kernel32')
local marker=ffi.new('uint16_t[20]',{67,72,90,90,75,79,118,101,114,108,97,121,79,119,110,101,114,0})
local O={};O.__index=O
function O.new()return setmetatable({pid=tonumber(kernel.GetCurrentProcessId()),locked=false,token=ffi.new('char[1]')},O)end
function O:windows()
 local found={};local pid=ffi.new('unsigned long[1]')
 local cb=ffi.cast('chzzk_enum_windows',function(hwnd)
  user.GetWindowThreadProcessId(hwnd,pid)
  if tonumber(pid[0])==self.pid then found[tostring(hwnd)]=hwnd end
  return 1
 end)
 user.EnumWindows(cb,0);cb:free();return found
end
jit.off(O.windows,true)
function O:valid()
 if not self.hwnd or user.IsWindow(self.hwnd)==0 then return false end
 local pid=ffi.new('unsigned long[1]');user.GetWindowThreadProcessId(self.hwnd,pid)
 return tonumber(pid[0])==self.pid and user.GetPropW(self.hwnd,marker)==ffi.cast('void*',self.token)
end
function O:adopt(before,source,width,height)
 for key,hwnd in pairs(self:windows())do
  if not before[key] then
   local title=ffi.new('uint16_t[512]');local n=user.GetWindowTextW(hwnd,title,512)
   local ascii={};for i=0,n-1 do ascii[#ascii+1]=title[i]<128 and string.char(title[i]) or '?' end
   if table.concat(ascii):find(source,1,true) then
    if user.SetPropW(hwnd,marker,ffi.cast('void*',self.token))==0 then return false end
    self.hwnd=hwnd;self.style=tonumber(user.GetWindowLongPtrW(hwnd,-16));self.exstyle=tonumber(user.GetWindowLongPtrW(hwnd,-20))
    self.locked=false;self.alpha=230
    user.SetWindowPos(hwnd,ffi.cast('void*',-1),80,80,width,height,0x10)
    return true
   end
  end
 end
 return false
end
function O:set_locked(locked,opacity)
 if not self:valid() then return false end
 self.locked=locked;self.alpha=math.floor(math.max(30,math.min(100,opacity or 90))*255/100)
 local style=self.style;local exstyle=bit.bor(self.exstyle,0x80000)
 if locked then style=bit.band(style,bit.bnot(0xc40000));exstyle=bit.bor(exstyle,0x20,0x08000000) end
 user.SetWindowLongPtrW(self.hwnd,-16,style);user.SetWindowLongPtrW(self.hwnd,-20,exstyle)
 user.SetLayeredWindowAttributes(self.hwnd,0,self.alpha,2)
 user.SetWindowPos(self.hwnd,ffi.cast('void*',-1),0,0,0,0,0x1+0x2+0x10+0x20)
 return true
end
function O:toggle(opacity)return self:set_locked(not self.locked,opacity)end
function O:show()if self:valid()then user.ShowWindow(self.hwnd,4)end end
function O:toggle_visible()if self:valid()then user.ShowWindow(self.hwnd,user.IsWindowVisible(self.hwnd)~=0 and 0 or 4)end end
function O:restore()
 if self:valid()then
  user.SetWindowLongPtrW(self.hwnd,-16,self.style);user.SetWindowLongPtrW(self.hwnd,-20,self.exstyle)
  user.RemovePropW(self.hwnd,marker)
  local top=bit.band(self.exstyle,8)~=0 and -1 or -2
  user.SetWindowPos(self.hwnd,ffi.cast('void*',top),0,0,0,0,0x1+0x2+0x10+0x20)
 end
 self.hwnd=nil
end
return O
