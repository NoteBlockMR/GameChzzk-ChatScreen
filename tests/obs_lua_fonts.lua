package.path='obs-plugin/?.lua;'..package.path
local fonts=require('chzzk_fonts').list();assert(#fonts>0)
local seen={};local arial=false
for _,name in ipairs(fonts)do assert(not seen[name] and name:sub(1,1)~='@');seen[name]=true;if name=='Arial' then arial=true end end
assert(arial)
assert(#require('chzzk_fonts').list()==#fonts)
print('FONT_LIST_OK: '..#fonts..' installed families, unique, repeat enumeration')
