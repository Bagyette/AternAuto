package fr.bagyette.aternauto.forge.compat.v1_14_4;

import fr.bagyette.aternauto.common.ClientUserAgent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.loading.FMLPaths;

@Mod("aternauto")
public final class AternAutoMod {
  public AternAutoMod() {
    ClientUserAgent.configure(FMLPaths.CONFIGDIR.get().resolve("aternauto"));
    if (net.minecraftforge.fml.loading.FMLEnvironment.dist
        == net.minecraftforge.api.distmarker.Dist.CLIENT) {
      net.minecraftforge.common.MinecraftForge.EVENT_BUS.register(new ForgeHooks());
    }
  }
}
