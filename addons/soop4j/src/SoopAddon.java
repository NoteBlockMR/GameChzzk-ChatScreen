import com.google.gson.Gson;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.logging.*;
import zzik2.soop4j.SoopClient;
import zzik2.soop4j.chat.*;
import zzik2.soop4j.chat.event.*;

/** Optional read-only chat bridge; no credentials or remote control endpoints. */
public final class SoopAddon implements AutoCloseable {
    static final int PORT = 18767;
    static final Gson JSON = new Gson();
    final String channel;
    final Deque<Map<String,Object>> messages = new ArrayDeque<>();
    final String session = UUID.randomUUID().toString();
    long sequence;
    String status = "연결 중";
    final SoopChat chat;
    final HttpServer server;
    final ExecutorService http = Executors.newFixedThreadPool(2);
    final ScheduledExecutorService timer = Executors.newSingleThreadScheduledExecutor();
    CompletableFuture<Void> connection;
    long retryAt, lastLog;
    volatile boolean closed;

    SoopAddon(String channel, boolean fixture) throws Exception {
        if (!channel.matches("[a-zA-Z0-9_]{1,64}")) throw new IllegalArgumentException("SOOP ID must contain only letters, digits or underscore (1-64).");
        this.channel = channel;
        // Bind before constructing a network client; a duplicate bridge must not connect.
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", PORT), 8);
        chat = fixture ? null : SoopClient.builder().build().chat(channel)
            .autoReconnect(true).reconnectDelayMs(10000).maxReconnectAttempts(Integer.MAX_VALUE)
            .connectTimeoutMs(15000).trustAllCertificates(false).build();
        server.setExecutor(http);
        server.createContext("/state", exchange -> {
            try {
                String host = exchange.getRequestHeaders().getFirst("Host");
                String origin = exchange.getRequestHeaders().getFirst("Origin");
                boolean allowedOrigin = origin == null || origin.equals("http://127.0.0.1:18766") || origin.equals("http://localhost:18766");
                int code = 200;
                if (!("127.0.0.1:"+PORT).equals(host) && !("localhost:"+PORT).equals(host)) code = 403;
                else if (!allowedOrigin) code = 403;
                else if (!exchange.getRequestURI().getPath().equals("/state")) code = 404;
                else if (!exchange.getRequestMethod().equals("GET")) code = 405;
                if (code == 200 && origin != null) exchange.getResponseHeaders().set("Access-Control-Allow-Origin", origin);
                byte[] body = (code == 200 ? snapshot() : "{}").getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
                exchange.getResponseHeaders().set("Cache-Control", "no-store");
                exchange.getResponseHeaders().set("Vary", "Origin");
                exchange.sendResponseHeaders(code, body.length);
                exchange.getResponseBody().write(body);
            } finally { exchange.close(); }
        });
        if (chat != null) chat.addListener(new SoopChatAdapter() {
            @Override public void onChat(ChatEvent event) {
                add(event.getUserId(), event.getUsername(), event.getMessage(), event.getReceivedTime().toEpochMilli());
            }
            @Override public void onDonation(DonationEvent event) { donation(event); }
            @Override public void onSubscribe(SubscribeEvent event) { subscription(event); }
            @Override public void onEnterChatRoom(EnterChatRoomEvent event) { setStatus("연결됨"); }
            @Override public void onDisconnect(DisconnectEvent event) { setStatus("재연결 대기"); }
            @Override public void onError(Exception error) { logFailure(); }
        });
        server.start();
        if (fixture) { setStatus("테스트"); add("fixture", "SOOP 테스트", "<b>문자 그대로 표시</b>", System.currentTimeMillis()); }
        else timer.scheduleWithFixedDelay(this::tick, 0, 1, TimeUnit.SECONDS);
    }
    synchronized void add(String user, String nickname, String content, long time) {
        addEvent(user,nickname,content,time,"chat");
    }
    void donation(DonationEvent event) {
        if (event.getType()==null || event.getAmount()<0) return;
        String title=event.getType()==DonationType.AD_BALLOON ? "애드벌룬 " :
            event.getType()==DonationType.VIDEO ? "영상 후원 · 별풍선 " : "별풍선 ";
        addEvent(event.getFrom(),event.getFromUsername(),title+event.getAmount()+"개",
            event.getReceivedTime().toEpochMilli(),"donation");
    }
    void subscription(SubscribeEvent event) {
        if (event.getMonthCount()<0) return;
        String text="구독 알림"+(event.getMonthCount()>0 ? " · "+event.getMonthCount()+"개월" : "");
        addEvent(event.getFrom(),event.getFromUsername(),text,event.getReceivedTime().toEpochMilli(),"subscription");
    }
    synchronized void addEvent(String user, String nickname, String content, long time, String kind) {
        if (user == null || nickname == null || content == null || content.length() > 8192) return;
        Map<String,Object> message = new LinkedHashMap<>();
        message.put("key", session+":"+(++sequence)); message.put("user",user);
        message.put("nickname",nickname); message.put("content",content); message.put("time",time);
        message.put("kind",kind);
        messages.addLast(message); while (messages.size()>100) messages.removeFirst();
    }
    synchronized void setStatus(String value) {
        if (!status.equals(value)) {
            status = value;
            // A transport reconnect is not a message deletion. Keep the bounded history.
            System.out.println("SOOP: "+value);
        }
    }
    synchronized void logFailure() {
        if (System.currentTimeMillis()-lastLog >= 60000) {
            lastLog=System.currentTimeMillis();
            System.err.println("SOOP connection error; retrying. Check that the channel is live and accessible.");
        }
    }
    synchronized String snapshot() {
        return JSON.toJson(Map.of("channel",channel,"status",status,"messages",new ArrayList<>(messages)));
    }
    void tick() {
        if (closed) return;
        try {
            if (chat.isEntered()) { setStatus("연결됨"); return; }
            setStatus("연결 중 / 재연결 대기");
            if (connection != null && !connection.isDone()) return;
            if (System.currentTimeMillis() < retryAt) return;
            retryAt = System.currentTimeMillis()+10000;
            connection = chat.connectAsync();
            connection.exceptionally(error -> { logFailure(); return null; });
        } catch (Exception error) { logFailure(); }
    }
    @Override public void close() {
        closed=true; timer.shutdownNow();
        if (chat != null) try { chat.disconnectAsync().get(3,TimeUnit.SECONDS); } catch (Exception ignored) {}
        server.stop(0); http.shutdownNow();
    }
    public static void main(String[] args) throws Exception {
        if (args.length < 1 || args.length > 2 || (args.length==2 && !args[1].equals("--fixture"))) {
            System.err.println("Usage: start.cmd SOOP_STREAMER_ID"); System.exit(2);
        }
        // Library exceptions may include raw network data. The adapter emits rate-limited diagnostics instead.
        Logger.getLogger("zzik2.soop4j.chat.SoopChat").setLevel(Level.OFF);
        SoopAddon addon = new SoopAddon(args[0], args.length==2);
        Runtime.getRuntime().addShutdownHook(new Thread(addon::close));
        System.out.println("SOOP addon ready: http://127.0.0.1:"+PORT+"/state ; Ctrl+C to stop");
        new CountDownLatch(1).await();
    }
}
