/* Display-only moderation adapter for the official CHZZK web chat.
 * Verified against the site's chat SDK: 94005 kick, 94008 blind,
 * 94015 penalty, 93006 event. Never infer sanctions from chat text.
 */
(() => {
  if (location.hostname !== 'chzzk.naver.com' || window.__gvModeration) return;
  window.__gvModeration = true;
  const purgedUntil = new Map();
  const deletedMessages = new Set();
  const selector = '[class*="live_chatting_list_item"], [class*="chatting_message"]';
  const id = value => typeof value === 'string' && value.length > 0 && value.length <= 256 ? value : null;
  const key = (user, time) => JSON.stringify([user, time]);
  let scheduled = false;
  let route = location.pathname;

  function resetRoute() {
    if (route !== location.pathname) {
      route = location.pathname;
      purgedUntil.clear(); deletedMessages.clear();
    }
  }

  function messageFor(element) {
    // Read only the specific chatMessage prop; never traverse arbitrary state.
    const prop = Object.keys(element).find(name => name.startsWith('__reactFiber$'));
    let fiber = prop && element[prop];
    for (let depth = 0; fiber && depth < 20; depth++, fiber = fiber.return) {
      const message = fiber.memoizedProps?.chatMessage;
      if (message && id(message.user) && Number.isFinite(message.time)) return message;
    }
    return null;
  }

  function scan() {
    scheduled = false;
    resetRoute();
    if (!document.body) return;
    for (const element of document.querySelectorAll(selector)) {
      if (element.parentElement?.closest(selector)) continue;
      const message = messageFor(element);
      // No nickname/text matching fallback: ambiguous rows must not be deleted.
      const hidden = message && (
        (purgedUntil.has(message.user) && message.time <= purgedUntil.get(message.user)) ||
        deletedMessages.has(key(message.user, message.time))
      );
      if (hidden) element.setAttribute('data-gv-moderated', '');
      else element.removeAttribute('data-gv-moderated');
    }
  }

  function schedule() {
    if (!scheduled) { scheduled = true; requestAnimationFrame(scan); }
  }

  function purge(user) {
    user = id(user);
    if (user) purgedUntil.set(user, Math.max(Date.now(), purgedUntil.get(user) || 0));
  }

  function receive(raw) {
    try {
      resetRoute();
      if (typeof raw !== 'string') return;
      const packet = JSON.parse(raw);
      const body = packet?.bdy;
      if (!body || typeof body !== 'object' || Array.isArray(body)) return;
      switch (packet.cmd) {
        case 94015:
          if (body.penaltyType === 'BAN' || body.penaltyType === 'MUTE') purge(body.userId);
          break;
        case 94005:
          if (Array.isArray(body.quitUserIdList)) body.quitUserIdList.forEach(purge);
          break;
        case 93006:
          if (body.type === 'TEMPORARY_RESTRICT' || body.type === 'RESTRICT_USER') purge(body.userIdHash);
          break;
        case 94008:
          if (!id(body.userId) || !Number.isFinite(body.messageTime)) break;
          if (body.blindType === 'CANCEL') deletedMessages.delete(key(body.userId, body.messageTime));
          else if (['BLIND', 'HIDDEN', 'RECLAIM', 'FILTERED', 'CBOTBLIND'].includes(body.blindType)) {
            deletedMessages.add(key(body.userId, body.messageTime));
          }
          break;
        default: return;
      }
      schedule();
    } catch { /* Unknown/malformed packets must not interrupt the official client. */ }
  }

  const NativeWebSocket = window.WebSocket;
  window.WebSocket = new Proxy(NativeWebSocket, {
    construct(Target, args, NewTarget) {
      const socket = Reflect.construct(Target, args, NewTarget);
      try {
        const url = new URL(args[0]);
        if (url.protocol === 'wss:' && url.hostname.endsWith('.nchat.naver.com')) {
          socket.addEventListener('message', event => receive(event.data));
        }
      } catch { /* Keep native WebSocket behavior. */ }
      return socket;
    }
  });

  function start() {
    const style = document.createElement('style');
    style.textContent = '[data-gv-moderated] { display:none !important; }';
    document.head.appendChild(style);
    new MutationObserver(schedule).observe(document.body, {
      childList:true, subtree:true, characterData:true, attributes:true, attributeFilter:['class']
    });
    // React may recycle rows without replacing their DOM nodes.
    setInterval(scan, 500);
    schedule();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
})();
