import zzik2.soop4j.chat.event.*;
public class SoopHistoryTest {
 public static void main(String[] args) throws Exception {
  try(SoopAddon addon=new SoopAddon("fixture_soop",true)) {
   addon.add("u","test","keep",1);
   addon.donation(new DonationEvent(DonationType.TEXT,"fixture_soop","u","donor",100,0));
   addon.donation(new DonationEvent(DonationType.VIDEO,"fixture_soop","u","donor",200,0));
   addon.donation(new DonationEvent(DonationType.AD_BALLOON,"fixture_soop","u","donor",3,0));
   addon.subscription(new SubscribeEvent("fixture_soop","u","subscriber",6,1));
   if(addon.messages.stream().filter(m->"donation".equals(m.get("kind"))).count()!=3)throw new AssertionError("Donation variants missing");
   if(!"subscription".equals(addon.messages.getLast().get("kind")))throw new AssertionError("Subscription missing");
   int count=addon.messages.size();addon.donation(new DonationEvent(DonationType.TEXT,"fixture_soop","u","donor",-1,0));
   if(count!=addon.messages.size())throw new AssertionError("Invalid amount accepted");
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
