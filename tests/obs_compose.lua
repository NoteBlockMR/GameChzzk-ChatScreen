-- Exercise scene composition through the actual script callbacks.
local sources,buttons,properties={},{},{}
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
function o.obs_sceneitem_set_order(i,movement)
 assert(movement==o.OBS_ORDER_MOVE_TOP)
 i.scene.top=i
end
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
for _,kind in ipairs({'text','int','list','bool'})do o['obs_properties_add_'..kind]=function(p,key)local value={};properties[key]=value;return value end end
function o.obs_property_set_enabled(p,v)p.enabled=v end
function o.obs_source_properties(s)return {video_device_id=s.devices or {}} end
function o.obs_properties_get(p,key)return p[key] end
function o.obs_properties_destroy()end
function o.obs_property_list_item_count(p)return #p end
function o.obs_property_list_item_string(p,i)return p[i+1].id end
function o.obs_property_list_item_name(p,i)return p[i+1].name end
function o.obs_property_list_item_disabled(p,i)return p[i+1].disabled or false end
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
assert(properties.camera_enabled.enabled==false)
local scene=sources['CHZZK 게임 + 채팅'];local game=o.obs_scene_find_source(scene,'Game');local chat=o.obs_scene_find_source(scene,'CHZZK Chat Lounge (OBS)')
assert(game.transform.alignment==5 and game.transform.bounds_alignment==0)
assert(game.transform.bounds.x==1540 and game.transform.bounds.y==1080)
assert(chat.transform.pos.x==1540 and chat.transform.bounds.x==380)
assert(sources['CHZZK Chat Lounge (OBS)'].settings.height==1080)
assert(buttons.compose());local count=0;for _ in pairs(scene.items)do count=count+1 end;assert(count==2)
assert(config.composition_layout=='side_by_side' and scene.top==chat)
config.composition_layout='overlay';assert(buttons.compose())
assert(game.transform.bounds.x==1920 and game.transform.bounds.y==1080)
assert(chat.transform.pos.x==1540 and scene.top==chat)
config.composition_layout='side_by_side';assert(buttons.compose())
assert(game.transform.bounds.x==1540)
o.obs_source_create('window_capture','Window',{});config.game='Window';cw=1280;ch=720
assert(buttons.compose());assert(not o.obs_scene_find_source(scene,'Game'));assert(o.obs_scene_find_source(scene,'Window').transform.bounds.x==900)
config.width=5000;assert(buttons.compose());assert(o.obs_scene_find_source(scene,'Window').transform.bounds.x==640)
config.composition_layout='overlay';assert(buttons.compose())
assert(o.obs_scene_find_source(scene,'Window').transform.bounds.x==1280)
assert(chat.transform.pos.x==640 and chat.transform.bounds.x==640 and scene.top==chat)
o.obs_source_create('game_capture','Replacement',{});config.game='Replacement'
assert(buttons.compose());assert(not o.obs_scene_find_source(scene,'Window'))
assert(scene.top==chat and o.obs_scene_find_source(scene,'Replacement').transform.bounds.x==1280)
count=0;for _ in pairs(scene.items)do count=count+1 end;assert(count==2)
-- Only present virtual devices may be added; physical and OBS cameras are excluded.
local cam=o.obs_source_create('dshow_input','Avatar',{video_device_id='avatar'})
cam.devices={{id='avatar',name='VSeeFace Virtual Camera'}}
script_properties();assert(properties.camera_enabled.enabled)
config.camera_enabled=true;config.camera_source='Avatar';assert(buttons.compose())
local avatar=o.obs_scene_find_source(scene,'Avatar')
assert(avatar and avatar.transform.pos.y==432 and avatar.transform.bounds.y==288 and scene.top==chat)
assert(buttons.compose());count=0;for _ in pairs(scene.items)do count=count+1 end;assert(count==3)
cam.devices[1].disabled=true;assert(buttons.compose()==false)
cam.devices[1].disabled=false;cam.devices[1].name='USB Webcam';assert(buttons.compose()==false)
cam.devices[1].name='OBS Virtual Camera';assert(buttons.compose()==false)
cam.devices[1].name='VSeeFace Virtual Camera'
local cam2=o.obs_source_create('dshow_input','Avatar2',{video_device_id='avatar2'})
cam2.devices={{id='avatar2',name='Animaze Virtual Camera'}}
config.camera_source='Avatar2';assert(buttons.compose())
assert(not o.obs_scene_find_source(scene,'Avatar') and o.obs_scene_find_source(scene,'Avatar2'))
config.camera_enabled=false;assert(buttons.compose());assert(not o.obs_scene_find_source(scene,'Avatar2'))
cam.devices={};cam2.devices={};config.camera_enabled=true
script_properties();assert(not properties.camera_enabled.enabled and not config.camera_enabled)
-- Official alerts: validation, ownership, layout, repeat update, shutdown.
config.donation_enabled=true;config.donation_url='https://chzzk.naver.com.evil.test/alert'
local before_donation=serial;assert(buttons.compose()==false and serial==before_donation)
config.donation_url='https://chzzk.naver.com/alert/test-fixture'
config.video_donation_enabled=true;config.video_donation_url='https://chzzk.naver.com/video-donation/video@test-fixture?ui=true'
assert(buttons.compose())
local alert=sources['CHZZK 공식 후원 알림'];local video_alert=sources['CHZZK 공식 영상 후원']
assert(alert.settings.reroute_audio and alert.settings.shutdown)
assert(video_alert.settings.url==config.video_donation_url)
assert(o.obs_scene_find_source(scene,alert.name).transform.pos.y==0)
assert(scene.top==o.obs_scene_find_source(scene,video_alert.name))
local alert_settings=alert.settings;assert(buttons.compose());assert(alert.settings==alert_settings)
config.composition_layout='side_by_side';assert(buttons.compose())
assert(video_alert.settings.width==384)
config.mission_donation_enabled=true;config.mission_donation_url=''
assert(buttons.compose()==false)
config.mission_donation_url='https://chzzk.naver.com/mission/test-fixture'
assert(buttons.compose())
local mission=sources['CHZZK 공식 미션 후원']
local mission_item=o.obs_scene_find_source(scene,mission.name)
assert(mission.settings.width==448 and mission.settings.height==180)
assert(mission_item.transform.pos.y==540 and scene.top==mission_item)
local mission_settings=mission.settings;assert(buttons.compose());assert(mission.settings==mission_settings)
config.composition_layout='overlay';assert(buttons.compose())
assert(mission.settings.width==896 and mission_item.transform.pos.y==540)
config.mission_donation_enabled=false;assert(buttons.compose())
assert(mission.settings.url=='about:blank' and not o.obs_scene_find_source(scene,mission.name))
assert(o.obs_scene_find_source(scene,alert.name) and o.obs_scene_find_source(scene,video_alert.name))
config.mission_donation_enabled=true;assert(buttons.compose())
assert(o.obs_scene_find_source(scene,mission.name) and mission.settings.url==config.mission_donation_url)
config.mission_donation_enabled=false
config.donation_enabled=false;config.video_donation_enabled=false;assert(buttons.compose())
assert(not o.obs_scene_find_source(scene,alert.name) and not o.obs_scene_find_source(scene,video_alert.name))
assert(alert.settings.url=='about:blank' and video_alert.settings.url=='about:blank')
video_alert.settings.chzzk_donation_managed=false
assert(buttons.compose()==false,'must preserve unrelated source')
video_alert.settings.chzzk_donation_managed=true
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
print('OBS_COMPOSE_OK: split/overlay, virtual camera detection/exclusions/disconnect/replacement/removal, ordering, bounds, cleanup')
