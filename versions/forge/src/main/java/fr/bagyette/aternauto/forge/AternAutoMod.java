package fr.bagyette.aternauto.forge;

import fr.bagyette.aternauto.common.BuildVersion;
import net.minecraftforge.common.ForgeVersion;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.common.FMLCommonHandler;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.event.FMLInitializationEvent;

@Mod(
    modid = "aternauto",
    name = "AternAuto",
    version = BuildVersion.VERSION,
    clientSideOnly = true,
    acceptedMinecraftVersions = "[1.8.9],[1.12.2]",
    acceptableRemoteVersions = "*")
public final class AternAutoMod {
  @Mod.EventHandler
  public void initialize(FMLInitializationEvent event) {
    ForgeHooks hooks = new ForgeHooks();
    MinecraftForge.EVENT_BUS.register(hooks);
    if (ForgeVersion.getMajorVersion() < 12) {
      FMLCommonHandler.instance().bus().register(hooks);
    }
  }
}
