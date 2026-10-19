"""공식 채팅의 동작을 유지하면서 읽기 쉬운 글꼴과 메시지 여백 적용."""
import json
from PySide6.QtWebEngineCore import QWebEngineScript


def theme_script(font_size=16):
    size = max(12, min(24, int(font_size)))
    css = f'''
:root {{ --gv-ink:#edf0ff; --gv-muted:#8f98b5; --gv-accent:#9e91ff; }}
html, body {{ font-family:"Malgun Gothic","Segoe UI",sans-serif !important; }}
body {{ background:#0e1020 !important; color:var(--gv-ink) !important; }}
[class*="chatting_list"], [class*="chatting_area"], [class*="chatting_content"] {{
    background:transparent !important;
}}
[class*="chatting_message"], [class*="chatting_list"] {{ font-size:{size}px !important; line-height:1.65 !important; }}
[data-gv-card] {{
    box-sizing:border-box !important;
    position:relative; margin:9px 12px !important; padding:13px 15px !important;
    background:linear-gradient(135deg,#20243a,#171b2e) !important;
    border:1px solid #343952 !important; border-left:3px solid var(--gv-person,#a799ff) !important;
    border-radius:15px 15px 15px 5px !important;
    box-shadow:0 5px 14px #05071355;
    color:var(--gv-ink) !important; overflow-wrap:anywhere;
    font-size:{size}px !important; line-height:1.65 !important;
}}
[data-gv-card] [class*="nickname"], [data-gv-card] [class*="username"] {{
    color:var(--gv-person,#b4a5ff) !important; font-weight:750 !important;
    font-size:0.82em !important; letter-spacing:0.2px;
}}
[data-gv-card] [class*="message_text"], [data-gv-card] [class*="message_content"] {{
    color:var(--gv-ink) !important;
}}
[data-gv-card] img {{ vertical-align:middle; }}
[data-gv-enter] {{ animation:gv-arrive .28s ease-out both; }}
@keyframes gv-arrive {{ from {{ opacity:0; transform:translateY(7px); }} to {{ opacity:1; transform:translateY(0); }} }}
@media (prefers-reduced-motion:reduce) {{ [data-gv-enter] {{ animation:none; }} }}
textarea, [contenteditable="true"] {{ border-radius:12px !important; background:#1c2035 !important; color:#edf0ff !important; }}
::-webkit-scrollbar {{ width:4px; }}
::-webkit-scrollbar-thumb {{ background:#625b8b; border-radius:8px; }}
::-webkit-scrollbar-track {{ background:transparent; }}
'''
    return '''(() => {
      if (location.hostname !== 'chzzk.naver.com') return;
      let style = document.getElementById('game-view-chat-theme');
      if (!style) { style = document.createElement('style'); style.id = 'game-view-chat-theme'; document.head.appendChild(style); }
      style.textContent = %s;
      if (window.__gvCardObserver) return;
      const selector = '[class*="live_chatting_list_item"], [class*="chatting_message"]';
      const colors = ['#ac9aff','#79dccc','#ffbb84','#9bbaff','#ee9fc9'];
      const decorate = (root, entering) => {
        const candidates = [];
        if (root.nodeType !== 1) return;
        if (root.matches(selector)) candidates.push(root);
        candidates.push(...root.querySelectorAll(selector));
        for (const el of candidates) {
          if (el.hasAttribute('data-gv-card') || el.parentElement?.closest(selector)) continue;
          if (el.matches('input,textarea,button') || el.isContentEditable) continue;
          const name = el.querySelector('[class*="nickname"], [class*="username"]');
          let hash = 0;
          for (const letter of (name?.textContent || 'chat')) hash = ((hash * 31) + letter.codePointAt(0)) >>> 0;
          el.style.setProperty('--gv-person', colors[hash %% colors.length]);
          el.setAttribute('data-gv-card', '');
          if (entering) el.setAttribute('data-gv-enter', '');
        }
      };
      decorate(document.body, false);
      window.__gvCardObserver = new MutationObserver(records => {
        for (const record of records) for (const node of record.addedNodes) decorate(node, true);
      });
      window.__gvCardObserver.observe(document.body, { childList:true, subtree:true });
    })();''' % json.dumps(css)


def apply_chat_theme(view, font_size=16):
    if hasattr(view, "set_font_size"):
        view.set_font_size(font_size)
        return
    scripts = view.page().scripts()
    for old in scripts.toList():
        if old.name() == 'game-view-chat-theme':
            scripts.remove(old)
    script = QWebEngineScript()
    script.setName('game-view-chat-theme')
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
    script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
    script.setRunsOnSubFrames(False)
    script.setSourceCode(theme_script(font_size))
    scripts.insert(script)
    view.page().runJavaScript(script.sourceCode(), QWebEngineScript.ScriptWorldId.ApplicationWorld)
