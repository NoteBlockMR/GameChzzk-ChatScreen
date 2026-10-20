obs = obslua
-- obs-defs.h alignment macros are absent in some Lua bindings.
local ALIGN_LEFT = obs.OBS_ALIGN_LEFT or 1
local ALIGN_TOP = obs.OBS_ALIGN_TOP or 4
local ALIGN_CENTER = obs.OBS_ALIGN_CENTER or 0
local setup_overlay,shutdown_overlay,save_overlay
local config
local source_name = 'CHZZK Chat Lounge (OBS)'
function script_description()
 return 'CHZZK 커스텀 채팅 실험 확장. Python 없이 OBS Lua가 직접 수신합니다. 채널 설정 → 소스 추가. Windows / OBS libcurl 필요. 게임은 OBS 게임 캡처를 사용하세요. 수신기 하나당 한 채널을 지원합니다.'
end
local function encode(value)
 return (value:gsub('([^%w%-_%.~])',function(c)return string.format('%%%02X',string.byte(c))end))
end
local receiver,server
local stop_receiver
local function tick_receiver()
 local ok,err=pcall(function()
  if receiver then receiver:tick() end
  if server then server:tick() end
 end)
 if not ok then
  stop_receiver()
  obs.script_log(obs.LOG_WARNING,'Lua 수신기 중지: '..tostring(err)..' · 설정 적용으로 다시 시작하세요.')
 end
end
stop_receiver=function()
 obs.timer_remove(tick_receiver)
 local old_server,old_receiver=server,receiver
 server=nil;receiver=nil
 if old_server then pcall(function()old_server:close()end) end
 if old_receiver then pcall(function()old_receiver:close()end) end
end
local function start_receiver(channel)
 local ok,err=pcall(function()
  local directory=script_path()
  package.path=directory..'?.lua;'..package.path
  local Receiver=require('chzzk_receiver')
  assert(Receiver.channel(channel),'올바른 치지직 채널 주소 / ID를 입력하세요.')
  if not receiver then
   receiver=Receiver.new(function(message,level)obs.script_log(level=='info' and obs.LOG_INFO or obs.LOG_WARNING,message)end)
   local file=assert(io.open(directory..'overlay.html','rb'))
   local html=file:read('*a');file:close()
   server=require('chzzk_http').new(html,function()return receiver:snapshot()end,18766)
   obs.timer_add(tick_receiver,30)
  end
  receiver:start(channel)
 end)
 if not ok then stop_receiver();obs.script_log(obs.LOG_WARNING,'Lua 수신기: '..tostring(err));return false end
 return true
end
function script_load(settings)
 setup_overlay(settings)
 local channel=obs.obs_data_get_string(settings,'channel')
 if channel~='' then start_receiver(channel) end
end
local function apply(props,prop,target_scene,chat_width,chat_height)
 local soop_id=obs.obs_data_get_string(config,'soop_channel'):match('^%s*(.-)%s*$')
 if obs.obs_data_get_bool(config,'soop_enabled') and (#soop_id<1 or #soop_id>64 or not soop_id:match('^[%w_]+$')) then
  obs.script_log(obs.LOG_WARNING,'SOOP 방송 ID를 입력하세요. 애드온 실행 시 입력한 ID와 같아야 합니다.')
  return false
 end
 local channel=obs.obs_data_get_string(config,'channel')
 if channel=='' then obs.script_log(obs.LOG_WARNING,'채널 주소를 입력하세요.');return false end
 if not start_receiver(channel) then return false end
 local settings=obs.obs_data_create()
 local url='http://127.0.0.1:18766/?channel='..encode(channel)..'&font='..encode(obs.obs_data_get_string(config,'font'))..'&size='..obs.obs_data_get_int(config,'size')
 if obs.obs_data_get_bool(config,'soop_enabled') then url=url..'&soop='..encode(soop_id) end
 obs.obs_data_set_string(settings,'url',url)
 obs.obs_data_set_int(settings,'width',chat_width or obs.obs_data_get_int(config,'width'))
 obs.obs_data_set_int(settings,'height',chat_height or obs.obs_data_get_int(config,'height'))
 obs.obs_data_set_bool(settings,'shutdown',false)
 obs.obs_data_set_bool(settings,'is_local_file',false)
 local source=obs.obs_get_source_by_name(source_name)
 if source and obs.obs_source_get_id(source)~='browser_source' then
  obs.script_log(obs.LOG_WARNING,'동일한 이름의 다른 종류 소스가 있습니다. 이름을 변경하세요.')
  obs.obs_source_release(source);obs.obs_data_release(settings);return false
 end
 if source then obs.obs_source_update(source,settings)
 else source=obs.obs_source_create('browser_source',source_name,settings,nil) end
 if source then
  if target_scene then
   if not obs.obs_scene_find_source(target_scene,source_name) then obs.obs_scene_add(target_scene,source) end
  else
  local current=obs.obs_frontend_get_current_scene()
  if current then
   local scene=obs.obs_scene_from_source(current)
   if scene and not obs.obs_scene_find_source(scene,source_name) then obs.obs_scene_add(scene,source) end
   obs.obs_source_release(current)
  end
  end
  obs.obs_source_release(source)
 else
  obs.script_log(obs.LOG_WARNING,'브라우저 소스를 만들 수 없습니다. obs-browser 설치를 확인하세요.')
  obs.obs_data_release(settings);return false
 end
 obs.obs_data_release(settings)
 return true
end
local overlay,overlay_key,pending_projector
local function overlay_opacity()
 return config and obs.obs_data_get_int(config,'overlay_opacity') or 90
end
local function find_projector()
 if not pending_projector then return end
 local task=pending_projector
 if overlay:adopt(task.before,source_name,task.width,task.height) then
  pending_projector=nil;obs.timer_remove(find_projector)
  overlay:set_locked(task.locked,overlay_opacity())
 elseif os.time()-task.started>5 then
  pending_projector=nil;obs.timer_remove(find_projector)
  obs.script_log(obs.LOG_WARNING,'채팅 프로젝터 창을 찾지 못했습니다. 열린 창을 닫고 다시 시도하세요.')
 end
end
local function open_overlay(locked)
 if not obs.obs_frontend_open_projector then obs.script_log(obs.LOG_WARNING,'OBS 프로젝터 API가 없습니다.');return false end
 if not overlay then
  package.path=script_path()..'?.lua;'..package.path
  local ok,module=pcall(require,'chzzk_overlay')
  if not ok then obs.script_log(obs.LOG_WARNING,'오버레이 초기화 실패: '..tostring(module));return false end
  overlay=module.new()
 end
 if overlay:valid()then overlay:show();overlay:set_locked(locked,overlay_opacity());return true end
 if pending_projector then return false end
 local source=obs.obs_get_source_by_name(source_name)
 if source then obs.obs_source_release(source) elseif not apply(nil,nil) then return false end
 pending_projector={before=overlay:windows(),width=obs.obs_data_get_int(config,'width'),height=obs.obs_data_get_int(config,'height'),started=os.time(),locked=locked}
 obs.obs_frontend_open_projector('Source',-1,'',source_name)
 obs.timer_add(find_projector,100)
 return true
end
local function toggle_overlay(pressed)
 if not pressed then return end
 if overlay and overlay:valid() then overlay:toggle(overlay_opacity()) else open_overlay(true) end
end
setup_overlay=function(settings)
 if not obs.obs_hotkey_register_frontend then return end
 overlay_key=obs.obs_hotkey_register_frontend('chzzk.game_overlay.toggle','CHZZK 게임 위 채팅 · 클릭 통과 전환',toggle_overlay)
 local bindings
 if obs.obs_data_has_user_value(settings,'overlay_hotkey') then
  bindings=obs.obs_data_get_array(settings,'overlay_hotkey')
 else
  local defaults=obs.obs_data_create_from_json('{"bindings":[{"key":"OBS_KEY_F8","control":true,"alt":true}]}')
  bindings=obs.obs_data_get_array(defaults,'bindings');obs.obs_data_release(defaults)
 end
 obs.obs_hotkey_load(overlay_key,bindings);obs.obs_data_array_release(bindings)
end
save_overlay=function(settings)
 if overlay_key then
  local bindings=obs.obs_hotkey_save(overlay_key)
  obs.obs_data_set_array(settings,'overlay_hotkey',bindings);obs.obs_data_array_release(bindings)
 end
end
function script_save(settings)save_overlay(settings)end
shutdown_overlay=function()
 obs.timer_remove(find_projector);pending_projector=nil
 if overlay then overlay:restore();overlay=nil end
 if overlay_key then obs.obs_hotkey_unregister(overlay_key);overlay_key=nil end
end
local capture_ids={game_capture=true,window_capture=true,monitor_capture=true}
local combined_name='CHZZK 게임 + 채팅'
-- Check the selected device against the current DirectShow device list.
-- Device names are a conservative heuristic, not proof of live video frames.
local function virtual_camera_label(source)
 if obs.obs_source_get_id(source)~='dshow_input' then return nil end
 local settings,properties
 local ok,label=pcall(function()
  settings=obs.obs_source_get_settings(source)
  local selected=obs.obs_data_get_string(settings,'video_device_id')
  if selected=='' then return nil end
  properties=obs.obs_source_properties(source)
  if not properties then return nil end
  local devices=obs.obs_properties_get(properties,'video_device_id')
  if not devices then return nil end
  for i=0,obs.obs_property_list_item_count(devices)-1 do
   if obs.obs_property_list_item_string(devices,i)==selected and not obs.obs_property_list_item_disabled(devices,i) then
    local name=obs.obs_property_list_item_name(devices,i)
    local lower=name:lower()
    -- Exclude OBS output to avoid feeding this composition back into itself.
    if lower:find('obs',1,true) then return nil end
    for _,token in ipairs({'virtual','가상','vtube','vseeface','vnyan','animaze','facerig','v magic','vmagic','manycam'}) do
     if lower:find(token,1,true) then return name end
    end
   end
  end
 end)
 if properties then obs.obs_properties_destroy(properties) end
 if settings then obs.obs_data_release(settings) end
 if ok then return label end
end
local function camera_options(p)
 local enabled=obs.obs_properties_add_bool(p,'camera_enabled','버추얼캠 함께 표시')
 local list=obs.obs_properties_add_list(p,'camera_source','감지된 버추얼캠 소스',obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
 obs.obs_property_list_add_string(list,'사용할 가상 카메라를 선택하세요','')
 local sources=obs.obs_enum_sources();local count=0
 if sources then
  for _,source in ipairs(sources) do
   local label=virtual_camera_label(source)
   if label then
    local name=obs.obs_source_get_name(source)
    obs.obs_property_list_add_string(list,name..' ('..label..')',name);count=count+1
   end
  end
  obs.source_list_release(sources)
 end
 obs.obs_property_set_enabled(enabled,count>0)
 obs.obs_property_set_enabled(list,count>0)
 if count==0 and config then obs.obs_data_set_bool(config,'camera_enabled',false) end
 obs.obs_properties_add_button(p,'refresh_cameras',count>0 and '버추얼캠 다시 감지' or '버추얼캠 미감지 · 다시 감지',function()return true end)
end
local function place(item,x,y,w,h)
 local position=obs.vec2()
 position.x=x;position.y=y
 local scale=obs.vec2()
 scale.x=1;scale.y=1
 local bounds=obs.vec2()
 bounds.x=w;bounds.y=h
 obs.obs_sceneitem_set_pos(item,position)
 obs.obs_sceneitem_set_scale(item,scale)
 obs.obs_sceneitem_set_rot(item,0)
 obs.obs_sceneitem_set_alignment(item,ALIGN_LEFT+ALIGN_TOP)
 obs.obs_sceneitem_set_bounds_type(item,obs.OBS_BOUNDS_SCALE_INNER)
 obs.obs_sceneitem_set_bounds_alignment(item,ALIGN_CENTER)
 obs.obs_sceneitem_set_bounds(item,bounds)
 local crop=obs.obs_sceneitem_crop()
 crop.left=0;crop.right=0;crop.top=0;crop.bottom=0
 obs.obs_sceneitem_set_crop(item,crop)
 obs.obs_sceneitem_set_visible(item,true)
end
local function composition_available()
 local required={'vec2','obs_sceneitem_set_pos','obs_sceneitem_set_scale',
  'obs_sceneitem_set_rot','obs_sceneitem_set_alignment','obs_sceneitem_set_bounds_type',
  'obs_sceneitem_set_bounds_alignment','obs_sceneitem_set_bounds','obs_sceneitem_crop',
  'obs_sceneitem_set_crop','obs_sceneitem_set_visible','obs_scene_find_sceneitem_by_id',
  'obs_sceneitem_get_id','obs_sceneitem_remove','obs_scene_add','obs_scene_create',
  'obs_video_info','obs_get_video_info','obs_sceneitem_set_order'}
 for _,name in ipairs(required) do
  if obs[name]==nil then
   obs.script_log(obs.LOG_WARNING,'합성 기능을 사용할 수 없습니다. OBS Lua API 누락: '..name)
   return false
  end
 end
 if obs.OBS_BOUNDS_SCALE_INNER==nil or obs.OBS_ORDER_MOVE_TOP==nil then return false end
 return true
end
local donation_sources={
 {key='donation',name='CHZZK 공식 후원 알림',label='후원 알림'},
 {key='video_donation',name='CHZZK 공식 영상 후원',label='영상 후원'},
 {key='mission_donation',name='CHZZK 공식 미션 후원',label='미션 후원'},
}
local function donation_url(entry)
 return obs.obs_data_get_string(config,entry.key..'_url'):match('^%s*(.-)%s*$')
end
local function validate_donations()
 for _,entry in ipairs(donation_sources) do
  if obs.obs_data_get_bool(config,entry.key..'_enabled') then
   local url=donation_url(entry)
   if not url:match('^https://chzzk%.naver%.com/[^%s]+$') or url:find('[%c]') then
    obs.script_log(obs.LOG_WARNING,entry.label..': 치지직 스튜디오에서 복사한 https://chzzk.naver.com/ 오버레이 주소를 입력하세요.')
    return false
   end
  end
  local source=obs.obs_get_source_by_name(entry.name)
  if source then
   local settings=obs.obs_source_get_settings(source)
   local owned=obs.obs_source_get_id(source)=='browser_source' and obs.obs_data_get_bool(settings,'chzzk_donation_managed')
   obs.obs_data_release(settings);obs.obs_source_release(source)
   if not owned then
    obs.script_log(obs.LOG_WARNING,entry.label..': 같은 이름의 기존 소스가 있습니다. 기존 소스 이름을 변경하세요.')
    return false
   end
  end
 end
 return true
end
local function apply_donation(scene,entry,game_width,canvas_height)
 local enabled=obs.obs_data_get_bool(config,entry.key..'_enabled')
 local source=obs.obs_get_source_by_name(entry.name)
 local settings=obs.obs_data_create()
 local ok=pcall(function()
  local is_video=entry.key=='video_donation'
  local is_mission=entry.key=='mission_donation'
  local width=math.max(1,math.floor(game_width*(is_video and 0.6 or 0.7)))
  local height=math.max(1,math.floor(is_video and math.min(width*9/16,canvas_height*0.6) or canvas_height*0.25))
  obs.obs_data_set_bool(settings,'chzzk_donation_managed',true)
  obs.obs_data_set_string(settings,'url',enabled and donation_url(entry) or 'about:blank')
  obs.obs_data_set_int(settings,'width',width);obs.obs_data_set_int(settings,'height',height)
  obs.obs_data_set_bool(settings,'is_local_file',false)
  obs.obs_data_set_bool(settings,'shutdown',true)
  obs.obs_data_set_bool(settings,'reroute_audio',true)
  if source then
   -- Avoid reloading the alert queue for unrelated layout changes.
   local old=obs.obs_source_get_settings(source)
   local changed=obs.obs_data_get_string(old,'url')~=obs.obs_data_get_string(settings,'url') or obs.obs_data_get_int(old,'width')~=width or obs.obs_data_get_int(old,'height')~=height
   obs.obs_data_release(old)
   if changed then obs.obs_source_update(source,settings) end
  elseif enabled then
   source=obs.obs_source_create('browser_source',entry.name,settings,nil)
   assert(source,'browser source unavailable')
  end
  local item=obs.obs_scene_find_source(scene,entry.name)
  if not enabled then
   if item then obs.obs_sceneitem_remove(item) end
   return
  end
  if not item then item=obs.obs_scene_add(scene,source) end
  assert(item,'scene item unavailable')
  local y=is_mission and canvas_height-height or (is_video and math.floor((canvas_height-height)/2) or 0)
  place(item,math.floor((game_width-width)/2),y,width,height)
  obs.obs_sceneitem_set_order(item,obs.OBS_ORDER_MOVE_TOP)
 end)
 obs.obs_data_release(settings)
 if source then obs.obs_source_release(source) end
 -- Never include exceptions that could contain the private overlay URL.
 assert(ok,entry.label..' 소스 적용 실패')
end
local function compose()
 if not composition_available() then return false end
 if not validate_donations() then return false end
 local camera_name=obs.obs_data_get_bool(config,'camera_enabled') and obs.obs_data_get_string(config,'camera_source') or ''
 if obs.obs_data_get_bool(config,'camera_enabled') then
  local camera=obs.obs_get_source_by_name(camera_name)
  local detected=camera and virtual_camera_label(camera)
  if camera then obs.obs_source_release(camera) end
  if not detected then
   obs.script_log(obs.LOG_WARNING,'버추얼캠을 찾을 수 없습니다. 비디오 캡처 장치 등록 후 다시 감지하거나 버추얼캠 설정을 해제하세요.')
   return false
  end
 end
 if obs.obs_data_get_string(config,'channel')=='' then obs.script_log(obs.LOG_WARNING,'채널 주소를 입력하세요.');return false end
 local game=obs.obs_get_source_by_name(obs.obs_data_get_string(config,'game'))
 if not game then obs.script_log(obs.LOG_WARNING,'먼저 OBS 게임/윈도우/디스플레이 캡처 소스를 만들고 선택하세요.');return false end
 if not capture_ids[obs.obs_source_get_id(game)] then obs.obs_source_release(game);return false end
 local video=obs.obs_video_info()
 if not obs.obs_get_video_info(video) or video.base_width<2 or video.base_height<1 then obs.obs_source_release(game);return false end
 local width=math.min(obs.obs_data_get_int(config,'width'),math.floor(video.base_width/2))
 width=math.max(1,width)
 local overlap=obs.obs_data_get_string(config,'composition_layout')=='overlay'
 local existing=obs.obs_get_source_by_name(combined_name)
 local scene,created,metadata
 if existing then
  scene=obs.obs_scene_from_source(existing)
  metadata=obs.obs_source_get_settings(existing)
  if not scene or not obs.obs_data_get_bool(metadata,'chzzk_managed') then
   obs.script_log(obs.LOG_WARNING,'CHZZK 게임 + 채팅 이름이 이미 사용 중입니다. 기존 소스의 이름을 변경하세요.')
   obs.obs_data_release(metadata);obs.obs_source_release(existing);obs.obs_source_release(game);return false
  end
 else
  scene=obs.obs_scene_create(combined_name);created=true
  if not scene then obs.obs_source_release(game);obs.script_log(obs.LOG_WARNING,'합성 장면 생성 실패');return false end
  metadata=obs.obs_source_get_settings(obs.obs_scene_get_source(scene))
  obs.obs_data_set_bool(metadata,'chzzk_managed',true)
 end
 local ok,result=pcall(function()
 if apply(nil,nil,scene,width,video.base_height) then
  local old=obs.obs_scene_find_sceneitem_by_id(scene,obs.obs_data_get_int(metadata,'chzzk_game_item'))
  local item=obs.obs_scene_find_source(scene,obs.obs_source_get_name(game))
  if old and old~=item then obs.obs_sceneitem_remove(old) end
  if not item then item=obs.obs_scene_add(scene,game) end
  obs.obs_data_set_int(metadata,'chzzk_game_item',obs.obs_sceneitem_get_id(item))
  place(item,0,0,overlap and video.base_width or video.base_width-width,video.base_height)
  local old_camera=obs.obs_scene_find_sceneitem_by_id(scene,obs.obs_data_get_int(metadata,'chzzk_camera_item'))
  local camera_item=camera_name~='' and obs.obs_scene_find_source(scene,camera_name) or nil
  if camera_name~='' and not camera_item then
   local camera=obs.obs_get_source_by_name(camera_name)
   assert(camera,'버추얼캠 소스가 제거되었습니다.')
   local added,value=pcall(obs.obs_scene_add,scene,camera)
   obs.obs_source_release(camera)
   assert(added and value,'버추얼캠 추가 실패');camera_item=value
  end
  if old_camera and old_camera~=camera_item then obs.obs_sceneitem_remove(old_camera) end
  obs.obs_data_set_int(metadata,'chzzk_camera_item',camera_item and obs.obs_sceneitem_get_id(camera_item) or 0)
  if camera_item then
   local game_width=overlap and video.base_width or video.base_width-width
   local camera_height=math.max(1,math.floor(video.base_height*0.4))
   place(camera_item,0,video.base_height-camera_height,math.max(1,math.floor(game_width*0.3)),camera_height)
   obs.obs_sceneitem_set_order(camera_item,obs.OBS_ORDER_MOVE_TOP)
  end
  local chat=obs.obs_scene_find_source(scene,source_name)
  if chat then
   place(chat,video.base_width-width,0,width,video.base_height)
   obs.obs_sceneitem_set_order(chat,obs.OBS_ORDER_MOVE_TOP)
  end
  local game_width=overlap and video.base_width or video.base_width-width
  for _,entry in ipairs(donation_sources) do apply_donation(scene,entry,game_width,video.base_height) end
  obs.script_log(obs.LOG_INFO,'CHZZK 게임 + 채팅 장면 준비 완료. 장면 목록에서 선택하세요.')
  return true
 end
 return false
 end)
 obs.obs_data_release(metadata)
 if created then obs.obs_scene_release(scene) else obs.obs_source_release(existing) end
 obs.obs_source_release(game)
 if not ok then obs.script_log(obs.LOG_WARNING,'합성 배치 실패: '..tostring(result));return false end
 return result
end
function script_properties()
 local p=obs.obs_properties_create()
 obs.obs_properties_add_text(p,'channel','치지직 채널 주소 / ID',obs.OBS_TEXT_DEFAULT)
 obs.obs_properties_add_bool(p,'soop_enabled','SOOP 채팅 함께 표시 (Java 애드온 필요)')
 obs.obs_properties_add_text(p,'soop_channel','SOOP 방송 ID (애드온과 동일)',obs.OBS_TEXT_DEFAULT)
 local fonts=obs.obs_properties_add_list(p,'font','채팅 폰트',obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
 local selected=config and obs.obs_data_get_string(config,'font') or 'Malgun Gothic'
 if selected=='' then selected='Malgun Gothic' end
 local ok,names=pcall(function()
  package.path=script_path()..'?.lua;'..package.path
  return require('chzzk_fonts').list()
 end)
 local found=false
 if ok then
  for _,name in ipairs(names) do
   obs.obs_property_list_add_string(fonts,name,name)
   if name==selected then found=true end
  end
 end
 if not found then obs.obs_property_list_add_string(fonts,selected..' (기존 설정)',selected) end
 obs.obs_properties_add_button(p,'refresh_fonts','설치된 폰트 목록 새로고침',function()return true end)
 obs.obs_properties_add_int(p,'overlay_opacity','게임 위 채팅 불투명도 (%)',30,100,5)
 obs.obs_properties_add_button(p,'overlay_open','게임 위 채팅 열기 · 이동/크기 편집',function()return open_overlay(false)end)
 obs.obs_properties_add_button(p,'overlay_lock','클릭 통과 전환 (Ctrl+Alt+F8)',function()toggle_overlay(true);return true end)
 obs.obs_properties_add_button(p,'overlay_hide','게임 위 채팅 숨기기 / 표시',function()if overlay then overlay:toggle_visible()end;return true end)
 obs.obs_properties_add_int(p,'size','글자 크기',12,48,1)
 obs.obs_properties_add_int(p,'width','채팅 폭',280,1920,10)
 obs.obs_properties_add_int(p,'height','채팅 높이',200,2160,10)
 local games=obs.obs_properties_add_list(p,'game','함께 출력할 캡처 소스',obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
 obs.obs_property_list_add_string(games,'캡처 소스를 선택하세요','')
 local sources=obs.obs_enum_sources()
 if sources then
  for _,source in ipairs(sources) do
   if capture_ids[obs.obs_source_get_id(source)] then
    local name=obs.obs_source_get_name(source);obs.obs_property_list_add_string(games,name,name)
   end
  end
  obs.source_list_release(sources)
 end
 obs.obs_properties_add_button(p,'refresh','캡처 소스 목록 새로고침',function() return true end)
 local layout=obs.obs_properties_add_list(p,'composition_layout','녹화 화면 배치',obs.OBS_COMBO_TYPE_LIST,obs.OBS_COMBO_FORMAT_STRING)
 obs.obs_property_list_add_string(layout,'나란히 — 게임 왼쪽 / 채팅 오른쪽','side_by_side')
 obs.obs_property_list_add_string(layout,'중첩 — 전체 게임 위에 채팅 표시','overlay')
 camera_options(p)
 for _,entry in ipairs(donation_sources) do
  obs.obs_properties_add_bool(p,entry.key..'_enabled',entry.label..' 표시 (합성 갱신 시 적용)')
  obs.obs_properties_add_text(p,entry.key..'_url',entry.label..' 공식 오버레이 주소',obs.OBS_TEXT_PASSWORD)
 end
 obs.obs_properties_add_button(p,'compose','게임 + 채팅 합성 장면 만들기 / 갱신',compose)
 obs.obs_properties_add_button(p,'apply','현재 장면에 채팅 추가 / 설정 적용',apply)
 return p
end
function script_defaults(s)
 obs.obs_data_set_default_bool(s,'soop_enabled',false)
 for _,entry in ipairs(donation_sources) do obs.obs_data_set_default_bool(s,entry.key..'_enabled',false) end
 obs.obs_data_set_default_bool(s,'camera_enabled',false)
 obs.obs_data_set_default_string(s,'composition_layout','side_by_side')
 obs.obs_data_set_default_int(s,'overlay_opacity',90)
 obs.obs_data_set_default_string(s,'font','Malgun Gothic')
 obs.obs_data_set_default_int(s,'size',20)
 obs.obs_data_set_default_int(s,'width',380)
 obs.obs_data_set_default_int(s,'height',720)
end
function script_update(s)
 if config then obs.obs_data_release(config) end
 config=s;obs.obs_data_addref(config)
end
function script_unload()
 shutdown_overlay()
 stop_receiver()
 if config then obs.obs_data_release(config);config=nil end
end
