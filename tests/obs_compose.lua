-- Exercise scene composition through the actual script callbacks.
local sources,buttons={},{}
obslua=setmetatable({OBS_BOUNDS_SCALE_INNER=2}, {__index=function(_,k) if k:match('^OBS_ALIGN_') then return nil end if k:match('^OBS_') or k=='LOG_WARNING' or k=='LOG_INFO' then return 0 end error(k) end})
local o=obslua
function o.obs_data_create() return {} end
function o.obs_data_get_string(s,k) return s[k] or '' end
function o.obs_data_get_int(s,k) return s[k] or 0 end
function o.obs_data_get_bool(s,k) return s[k] or false end
for _,kind in ipairs({'string','int','bool'}) do
 o['obs_data_set_'..kind]=function(s,k,v)s[k]=v end
 o['obs_data_set_default_'..kind]=function(s,k,v)if s[k]==nil then s[k]=v end end
end
function o.obs_data_addref()end
function o.obs_data_release()end
function o.obs_source_release()end
function o.obs_scene_release()end
function o.source_list_release()end
function o.script_log()end
function o.obs_get_source_by_name(n)return sources[n]end
function o.obs_source_get_id(s)return s.kind end
function o.obs_source_get_name(s)return s.name end
function o.obs_source_get_settings(s)return s.settings end
function o.obs_source_update(s,t)s.settings=t end
function o.obs_source_create(kind,name,settings) local s={kind=kind,name=name,settings=settings};sources[name]=s;return s end
function o.obs_scene_create(name)local s=o.obs_source_create('scene',name,{});s.items={};return s end
function o.obs_scene_get_source(s)return s end
function o.obs_scene_from_source(s)if s.kind=='scene' then return s end end
function o.obs_scene_find_source(s,n)for _,i in pairs(s.items)do if i.source.name==n then return i end end end
local serial=0
function o.obs_scene_add(s,source)serial=serial+1;local i={id=serial,source=source,scene=s};s.items[serial]=i;return i end
function o.obs_scene_find_sceneitem_by_id(s,id)return s.items[id]end
function o.obs_sceneitem_get_id(i)return i.id end
function o.obs_sceneitem_remove(i)i.scene.items[i.id]=nil end
function o.obs_video_info()return {}end
local cw,ch=1920,1080
function o.obs_get_video_info(v)v.base_width=cw;v.base_height=ch;return true end
-- The aggregate transform setter is deliberately unavailable.
function o.vec2()return {x=0,y=0}end
for _,field in ipairs({'pos','scale','rot','alignment','bounds_type','bounds_alignment','bounds'})do
 o['obs_sceneitem_set_'..field]=function(i,v)
  i.transform=i.transform or {};i.transform[field]=v
 end
end
function o.obs_sceneitem_crop()return {}end
function o.obs_sceneitem_set_crop(i,c)i.crop=c end
function o.obs_sceneitem_set_visible(i,v)i.visible=v end
function o.obs_properties_create()return {}end
for _,kind in ipairs({'text','int','list'})do o['obs_properties_add_'..kind]=function()return {}end end
function o.obs_property_list_add_string()end
function o.obs_properties_add_button(p,key,label,callback)buttons[key]=callback end
function o.obs_enum_sources()local t={};for _,s in pairs(sources)do table.insert(t,s)end;return t end

function script_path()return 'obs-plugin/'end
function o.timer_add()end
function o.timer_remove()end
package.loaded.chzzk_receiver={channel=function(s)return s end,new=function()return {start=function()end,close=function()end}end}
package.loaded.chzzk_http={new=function()return {close=function()end}end}
dofile('obs-plugin/chzzk-chat.lua')
local config={channel=string.rep('a',32),game='Game'}
script_defaults(config);script_update(config)
o.obs_source_create('game_capture','Game',{})
script_properties();assert(buttons.compose())
local scene=sources['CHZZK 게임 + 채팅'];local game=o.obs_scene_find_source(scene,'Game');local chat=o.obs_scene_find_source(scene,'CHZZK Chat Lounge (OBS)')
assert(game.transform.alignment==5 and game.transform.bounds_alignment==0)
assert(game.transform.bounds.x==1540 and game.transform.bounds.y==1080)
assert(chat.transform.pos.x==1540 and chat.transform.bounds.x==380)
assert(sources['CHZZK Chat Lounge (OBS)'].settings.height==1080)
assert(buttons.compose());local count=0;for _ in pairs(scene.items)do count=count+1 end;assert(count==2)
o.obs_source_create('window_capture','Window',{});config.game='Window';cw=1280;ch=720
assert(buttons.compose());assert(not o.obs_scene_find_source(scene,'Game'));assert(o.obs_scene_find_source(scene,'Window').transform.bounds.x==900)
config.width=5000;assert(buttons.compose());assert(o.obs_scene_find_source(scene,'Window').transform.bounds.x==640)
config.game='Missing';assert(buttons.compose()==false)
-- An exception while applying transforms must release owned references.
config.game='Window'
local releases,data_releases=0,0
local old_release,old_data_release=o.obs_source_release,o.obs_data_release
o.obs_source_release=function()releases=releases+1 end
o.obs_data_release=function()data_releases=data_releases+1 end
local old_pos=o.obs_sceneitem_set_pos
o.obs_sceneitem_set_pos=function()assert(false,'injected transform failure')end
assert(buttons.compose()==false)
assert(releases>=3 and data_releases>=2)
o.obs_source_release=old_release;o.obs_data_release=old_data_release
-- API availability is checked before any scene mutation.
local meta=getmetatable(o);local old_index=meta.__index
meta.__index=function(t,k)if k=='obs_sceneitem_set_pos' then return nil end;return old_index(t,k)end
o.obs_sceneitem_set_pos=nil
local before=serial
assert(buttons.compose()==false and serial==before)
o.obs_sceneitem_set_pos=old_pos;meta.__index=old_index
script_unload()
print('OBS_COMPOSE_OK: layout, repeat update, source replacement, width clamp, missing source')
