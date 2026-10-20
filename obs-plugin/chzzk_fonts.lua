-- Enumerate installed Windows font families without helper processes.
local ffi=require('ffi')
if not pcall(ffi.typeof,'struct chzzk_logfont') then
 ffi.cdef[[
 struct chzzk_logfont {int32_t height,width,escapement,orientation,weight;unsigned char italic,underline,strikeout,charset,outprecision,clipprecision,quality,pitch;uint16_t face[32];};
 typedef int (__stdcall *chzzk_font_callback)(const struct chzzk_logfont*,const void*,unsigned long,intptr_t);
 void *GetDC(void*); int ReleaseDC(void*,void*);
 int EnumFontFamiliesExW(void*,struct chzzk_logfont*,chzzk_font_callback,intptr_t,unsigned long);
 int WideCharToMultiByte(unsigned int,unsigned long,const uint16_t*,int,char*,int,const char*,int*);
 ]]
end
local user=ffi.load('user32');local gdi=ffi.load('gdi32');local kernel=ffi.load('kernel32')
local M={}
function M.list()
 local dc=assert(user.GetDC(nil),'GetDC failed')
 local filter=ffi.new('struct chzzk_logfont');filter.charset=1
 local result,seen={},{}
 local callback=ffi.cast('chzzk_font_callback',function(font)
  local buffer=ffi.new('char[256]')
  local n=kernel.WideCharToMultiByte(65001,0,font.face,-1,buffer,256,nil,nil)
  if n>1 then
   local name=ffi.string(buffer,n-1)
   if name:sub(1,1)~='@' and not seen[name] then seen[name]=true;result[#result+1]=name end
  end
  return 1
 end)
 gdi.EnumFontFamiliesExW(dc,filter,callback,0,0)
 callback:free();user.ReleaseDC(nil,dc)
 table.sort(result,function(a,b)return a:lower()<b:lower()end)
 return result
end
jit.off(M.list,true)
return M
