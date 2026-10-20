public class SoopHistoryTest {
 public static void main(String[] args) throws Exception {
  try(SoopAddon addon=new SoopAddon("fixture_soop",true)) {
   addon.add("u","test","keep",1);
   String before=addon.snapshot();
   addon.setStatus("reconnecting");
   if(!addon.snapshot().contains("keep"))throw new AssertionError("Reconnect deleted chat");
   addon.setStatus("connected");
   if(!addon.snapshot().contains("keep"))throw new AssertionError("Reconnection deleted chat");
   for(int i=0;i<150;i++)addon.add("u","test","m"+i,i);
   if(addon.messages.size()!=100)throw new AssertionError("History not bounded");
   System.out.println("SOOP_HISTORY_OK: reconnect retains messages; history capped at 100");
  }
 }
}
