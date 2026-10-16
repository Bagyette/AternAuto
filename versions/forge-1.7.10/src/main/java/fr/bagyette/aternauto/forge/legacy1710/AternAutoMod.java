package fr.bagyette.aternauto.forge.legacy1710;

import cpw.mods.fml.common.FMLCommonHandler;
import cpw.mods.fml.common.Mod;
import cpw.mods.fml.common.event.FMLInitializationEvent;
import fr.bagyette.aternauto.common.BuildVersion;
import net.minecraftforge.common.ForgeVersion;
import net.minecraftforge.common.MinecraftForge;

@Mod(
    modid = "aternauto",
    name = "AternAuto",
    version = BuildVersion.VERSION,
    acceptedMinecraftVersions = "[1.7.10]",
    acceptableRemoteVersions = "*")
@cpw.mods.fml.relauncher.SideOnly(cpw.mods.fml.relauncher.Side.CLIENT)
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
