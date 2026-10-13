package fr.bagyette.aternauto.forge;

import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.event.FMLInitializationEvent;

@Mod(
    modid = "aternauto",
    name = "AternAuto",
    version = "1",
    clientSideOnly = true,
    acceptedMinecraftVersions = "[1.8.9],[1.12.2]",
    acceptableRemoteVersions = "*")
public final class AternAutoMod {
  @Mod.EventHandler
  public void initialize(FMLInitializationEvent event) {
    MinecraftForge.EVENT_BUS.register(new ForgeHooks());
  }
}
