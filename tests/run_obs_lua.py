"""Execute Lua regression scripts with the installed OBS LuaJIT (test tool only)."""
import ctypes,os,sys
obsdir=r'C:\Program Files\obs-studio\bin\64bit'
os.add_dll_directory(obsdir)
lua=ctypes.CDLL(obsdir+r'\lua51.dll')
lua.luaL_newstate.restype=ctypes.c_void_p
for name in ['luaL_openlibs','lua_close']:getattr(lua,name).argtypes=[ctypes.c_void_p]
lua.luaL_loadfile.argtypes=[ctypes.c_void_p,ctypes.c_char_p]
lua.lua_pcall.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int]
lua.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p];lua.lua_tolstring.restype=ctypes.c_char_p
state=lua.luaL_newstate();lua.luaL_openlibs(state)
try:
 result=lua.luaL_loadfile(state,sys.argv[1].encode())
 if result==0:result=lua.lua_pcall(state,0,0,0)
 if result:raise RuntimeError(lua.lua_tolstring(state,-1,None).decode(errors='replace'))
finally:lua.lua_close(state)
